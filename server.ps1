# Travel Planner V4 - PowerShell 7 local web server
param([int]$Port = 8787)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$db = Join-Path $root 'data/trips.json'
$www = Join-Path $root 'www'
$recordsFile = Join-Path $root 'data/records.json'
$localPlacesFile = Join-Path $root 'data/places-local.json'
$placesCacheFile = Join-Path $root 'data/places-cache.json'
if (!(Test-Path $recordsFile)) { '{}' | Set-Content -LiteralPath $recordsFile -Encoding utf8 }
if (!(Test-Path $db)) { '[]' | Set-Content -LiteralPath $db -Encoding utf8 }
function Respond($ctx, [int]$status, [string]$body, [string]$type='application/json; charset=utf-8') {
  $bytes=[Text.Encoding]::UTF8.GetBytes($body)
  $ctx.Response.StatusCode=$status
  $ctx.Response.ContentType=$type
  $ctx.Response.ContentLength64=$bytes.Length
  $ctx.Response.OutputStream.Write($bytes,0,$bytes.Length)
  $ctx.Response.Close()
}
function Json($obj) { return ConvertTo-Json -InputObject $obj -Depth 20 -Compress }
function ReadBody($req) { $r=[IO.StreamReader]::new($req.InputStream,[Text.Encoding]::UTF8); try { return $r.ReadToEnd() } finally { $r.Dispose() } }
function GetTrips { $raw=Get-Content -LiteralPath $db -Raw -Encoding utf8; return ,@((ConvertFrom-Json -InputObject $raw)) }
function SaveTrips($items) { $temp="$db.tmp"; [IO.File]::WriteAllText($temp,(Json @($items)),[Text.UTF8Encoding]::new($false)); Move-Item -LiteralPath $temp -Destination $db -Force }
function ValidateTrip($o) {
  if (!$o.name -or [string]$o.name -notmatch '\S') { throw 'Le nom est obligatoire.' }
  $name=([string]$o.name).Trim(); if ($name.Length -gt 150) { throw 'Nom trop long.' }
  $kind=[string]$o.kind; if ($kind -notin @('past','future')) { throw 'Type de voyage invalide.' }
  $start=[string]$o.start; $end=[string]$o.end
  foreach($d in @($start,$end)) { if ($d -and $d -notmatch '^\d{4}-\d{2}-\d{2}$') { throw 'Date invalide.' } }
  if ($start -and $end -and $end -lt $start) { throw 'La date de fin précède le début.' }
  $lat=$null; $lon=$null
  if ($null -ne $o.lat -and "$($o.lat)" -ne '') { $lat=[double]$o.lat; if ($lat -lt -90 -or $lat -gt 90) { throw 'Latitude invalide.' } }
  if ($null -ne $o.lon -and "$($o.lon)" -ne '') { $lon=[double]$o.lon; if ($lon -lt -180 -or $lon -gt 180) { throw 'Longitude invalide.' } }
  return @{id= if($o.id -and [guid]::TryParse([string]$o.id,[ref]([guid]::Empty))){[string]$o.id}else{[guid]::NewGuid().ToString()};name=$name;country=([string]$o.country).Trim();kind=$kind;start=$start;end=$end;notes=([string]$o.notes);lat=$lat;lon=$lon}
}
function Remote($url) { return Invoke-RestMethod -Uri $url -Headers @{'User-Agent'='TravelPlannerPersonal/1.0 (local educational app)';'Accept'='application/json'} -TimeoutSec 18 }
$listener=[Net.HttpListener]::new()
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Prefixes.Add("http://192.168.1.191:$Port/")
$listener.Start()
Write-Host "Travel Planner : http://localhost:$Port/  (Ctrl+C pour arrêter)" -ForegroundColor Green
Write-Host "Acces Wi-Fi prive : http://192.168.1.191:$Port/"
try {
 while($listener.IsListening) {
  $ctx=$listener.GetContext()
  try {
   $req=$ctx.Request; $path=$req.Url.AbsolutePath; $method=$req.HttpMethod
   # Autoriser uniquement localhost et l'adresse Wi-Fi privee du PC.
   $hostName=([string]$req.Url.Host).ToLowerInvariant()
   if ($hostName -notin @('localhost','127.0.0.1','[::1]','192.168.1.191')) {
     Respond $ctx 403 '{"error":"Hote non autorise"}'; continue
   }
   if ($method -in @('POST','PUT','DELETE')) {
     $origin=[string]$req.Headers['Origin']
     if ($origin) {
       $parsedOrigin=$null
       if (-not [uri]::TryCreate($origin,[UriKind]::Absolute,[ref]$parsedOrigin) -or
           $parsedOrigin.Host -ne $req.Url.Host -or $parsedOrigin.Scheme -ne $req.Url.Scheme -or $parsedOrigin.Port -ne $req.Url.Port) {
         Respond $ctx 403 '{"error":"Origine non autorisee"}'; continue
       }
     }
   }
   if ($path -eq '/api/records' -and $method -eq 'GET') {
    Respond $ctx 200 ([IO.File]::ReadAllText($recordsFile,[Text.Encoding]::UTF8)); continue
   }
   if ($path -eq '/api/records' -and $method -eq 'PUT') {
    if ($req.ContentLength64 -gt 12000000) { throw 'Données trop volumineuses (12 Mo maximum).' }
    $raw=ReadBody $req
    if ($raw.Length -gt 12000000) { throw 'Données trop volumineuses.' }
    $o=ConvertFrom-Json -InputObject $raw
    if ($null -eq $o -or $o -isnot [pscustomobject]) { throw 'Objet JSON attendu.' }
    $temp="$recordsFile.tmp"
    [IO.File]::WriteAllText($temp,(Json $o),[Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temp -Destination $recordsFile -Force
    Respond $ctx 200 '{"ok":true}'; continue
   }
   if ($path -eq '/api/trips' -and $method -eq 'GET') { Respond $ctx 200 (Json (GetTrips)); continue }
   if ($path -eq '/api/trips' -and $method -eq 'POST') {
    $o=ConvertFrom-Json -InputObject (ReadBody $req); $trip=ValidateTrip $o
    $items=@(GetTrips); $items+= $trip; SaveTrips $items
    Respond $ctx 200 (Json $trip); continue
   }
   if ($path -match '^/api/trips/([a-fA-F0-9-]{36})$' -and $method -in @('PUT','DELETE')) {
    $id=$Matches[1]; $items=@(GetTrips); $found=@($items | Where-Object {$_.id -eq $id})
    if (!$found.Count) { Respond $ctx 404 '{"error":"Voyage introuvable"}'; continue }
    if ($method -eq 'DELETE') { SaveTrips @($items | Where-Object {$_.id -ne $id}); Respond $ctx 200 '{"ok":true}'; continue }
    $o=ConvertFrom-Json -InputObject (ReadBody $req); $o | Add-Member -NotePropertyName id -NotePropertyValue $id -Force
    $trip=ValidateTrip $o; SaveTrips @($items | ForEach-Object {if ($_.id -eq $id) {$trip} else {$_}})
    Respond $ctx 200 (Json $trip); continue
   }
   if ($path -eq '/api/geocode' -and $method -eq 'GET') {
    $q=[string]$req.QueryString['q']; if ($q.Length -lt 2 -or $q.Length -gt 150) { throw 'Recherche invalide.' }
    $results=@()
    try { $results=@(Remote ('https://nominatim.openstreetmap.org/search?format=json&limit=5&q='+[uri]::EscapeDataString($q))) } catch { Write-Warning ('Nominatim : '+$_.Exception.Message) }
    if ($results.Count -eq 0) {
      try {
        $photon=Remote ('https://photon.komoot.io/api/?limit=5&q='+[uri]::EscapeDataString($q))
        $results=@($photon.features | Where-Object { $_.geometry.coordinates.Count -ge 2 } | ForEach-Object {
          @{lat=$_.geometry.coordinates[1];lon=$_.geometry.coordinates[0];display_name=([string]$_.properties.name+', '+[string]$_.properties.country)}
        })
      } catch { Write-Warning ('Photon : '+$_.Exception.Message) }
    }
    Respond $ctx 200 (Json @($results)); continue
   }
   if ($path -eq '/api/route' -and $method -eq 'GET') {
    $coords=[string]$req.QueryString['coords']; $profile=[string]$req.QueryString['profile']
    if ($profile -notin @('driving','walking','cycling')) { throw 'Mode de trajet invalide.' }
    if ($coords.Length -gt 450 -or $coords -notmatch '^-?[0-9.]+,-?[0-9.]+(;-?[0-9.]+,-?[0-9.]+){1,9}$') { throw 'Coordonnees invalides.' }
    foreach($pair in ($coords -split ';')) {
      $xy=$pair -split ','; $x=0.0; $y=0.0
      if (![double]::TryParse($xy[0],[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$x) -or ![double]::TryParse($xy[1],[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$y) -or [math]::Abs($x) -gt 180 -or [math]::Abs($y) -gt 90) { throw 'Coordonnees hors limites.' }
    }
    # Public OSRM demo supports driving only; do not mislabel car routes as walking/cycling.
    if ($profile -ne 'driving') { throw 'Seul le calcul routier en voiture est disponible dans cette version.' }
    $url='https://router.project-osrm.org/route/v1/driving/'+$coords+'?overview=full&geometries=geojson&steps=false'
    Respond $ctx 200 (Json (Remote $url)); continue
   }
   if ($path -eq '/api/places' -and $method -eq 'GET') {
    # Resolve the offline city catalog BEFORE checking coordinates. This avoids
    # rejecting a known city when geocoding provides missing/invalid coordinates.
    $city=([string]$req.QueryString['city']).Trim().ToLowerInvariant()
    $city=[string]::Join('',($city.Normalize([Text.NormalizationForm]::FormD).ToCharArray() | Where-Object { [Globalization.CharUnicodeInfo]::GetUnicodeCategory($_) -ne [Globalization.UnicodeCategory]::NonSpacingMark }))
    # Curated city catalogs are available immediately, regardless of network status.
    # Prefer reliable offline results for known cities; unknown cities still use live Overpass.
    $aliases=@{'koeln'='cologne';'koln'='cologne';'köln'='cologne'}
    if ($aliases.ContainsKey($city)) { $city=$aliases[$city] }
    if (Test-Path -LiteralPath $localPlacesFile) {
      try {
        $catalog=Get-Content -LiteralPath $localPlacesFile -Raw -Encoding utf8 | ConvertFrom-Json
        $entry=$catalog.PSObject.Properties[$city]
        if ($null -ne $entry -and @($entry.Value).Count -gt 0) {
          $localItems=@($entry.Value)
          $center=@{lat=[double]$localItems[0].lat;lon=[double]$localItems[0].lon}
          Respond $ctx 200 (Json @{elements=$localItems;source='local';center=$center}); continue
        }
      } catch { Write-Warning ('Catalogue local : '+$_.Exception.Message) }
    }
    $lat=0.0; $lon=0.0
    $latText=([string]$req.QueryString['lat']).Replace(',', '.')
    $lonText=([string]$req.QueryString['lon']).Replace(',', '.')
    $style=[Globalization.NumberStyles]::Float
    $culture=[Globalization.CultureInfo]::InvariantCulture
    $validLat=[double]::TryParse($latText,$style,$culture,[ref]$lat)
    $validLon=[double]::TryParse($lonText,$style,$culture,[ref]$lon)
    if (-not $validLat -or -not $validLon -or [double]::IsNaN($lat) -or [double]::IsNaN($lon) -or [math]::Abs($lat) -gt 90 -or [math]::Abs($lon) -gt 180 -or ($lat -eq 0 -and $lon -eq 0)) {
      # Geocode by city name as a second chance; supports cities not yet in the offline catalog.
      if ($city.Length -lt 2) { throw "Indique le nom d'une ville." }
      try {
        $lookup=@()
        try { $lookup=@(Remote ('https://nominatim.openstreetmap.org/search?format=json&limit=1&q='+[uri]::EscapeDataString($city))) } catch { Write-Warning ('Géocodage Nominatim : '+$_.Exception.Message) }
        if ($lookup.Count -gt 0) {
          $lat=[double]::Parse([string]$lookup[0].lat,[Globalization.CultureInfo]::InvariantCulture)
          $lon=[double]::Parse([string]$lookup[0].lon,[Globalization.CultureInfo]::InvariantCulture)
        } else {
          $photon=Remote ('https://photon.komoot.io/api/?limit=1&q='+[uri]::EscapeDataString($city))
          if (@($photon.features).Count -eq 0) { throw 'Ville non reconnue.' }
          $lat=[double]$photon.features[0].geometry.coordinates[1]
          $lon=[double]$photon.features[0].geometry.coordinates[0]
        }
      } catch { throw ('Ville introuvable ou géocodage indisponible : '+$city+'. Réessaie avec Internet.') }
    }
    # Cities not in the curated offline catalog are discovered from OpenStreetMap.
    # Persist successful results so subsequent visits work even without internet.
    $cacheKey=(($city -replace '[^a-z0-9 -]','').Trim()+'_'+[math]::Round($lat,2)+'_'+[math]::Round($lon,2)) -replace ',','.'
    function ValidTouristItems($inputItems, [double]$cityLat, [double]$cityLon) {
      $valid=@()
      foreach($item in @($inputItems)) {
        if ($null -eq $item -or $null -eq $item.tags) { continue }
        $name=[string]$item.tags.name
        if ([string]::IsNullOrWhiteSpace($name) -or $name -match '(?i)^(null island|bouée soul)$') { continue }
        $coord=if ($null -ne $item.center) { $item.center } else { $item }
        if ($null -eq $coord -or $null -eq $coord.lat -or $null -eq $coord.lon) { continue }
        $pLat=0.0; $pLon=0.0
        if (-not [double]::TryParse(([string]$coord.lat).Replace(',','.'),[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$pLat)) { continue }
        if (-not [double]::TryParse(([string]$coord.lon).Replace(',','.'),[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$pLon)) { continue }
        if (([math]::Abs($pLat) -gt 90) -or ([math]::Abs($pLon) -gt 180) -or (($pLat -eq 0) -and ($pLon -eq 0))) { continue }
        $r=[math]::PI/180
        $h=[math]::Pow([math]::Sin(($pLat-$cityLat)*$r/2),2)+[math]::Cos($cityLat*$r)*[math]::Cos($pLat*$r)*[math]::Pow([math]::Sin(($pLon-$cityLon)*$r/2),2)
        $distance=6371*2*[math]::Asin([math]::Sqrt([math]::Min(1,[math]::Max(0,$h))))
        if ($distance -le 12) { $valid+= $item }
      }
      return $valid
    }
    $cachedItems=@()
    if (Test-Path -LiteralPath $placesCacheFile) {
      try {
        $saved=Get-Content -LiteralPath $placesCacheFile -Raw -Encoding utf8 | ConvertFrom-Json
        $cached=$saved.PSObject.Properties[$cacheKey]
        if ($null -ne $cached -and @($cached.Value).Count -gt 0) { $cachedItems=@(ValidTouristItems -inputItems @($cached.Value) -cityLat $lat -cityLon $lon) }
      } catch { Write-Warning ('Cache touristique : '+$_.Exception.Message) }
    }
    # Use cached results instantly when available; online discovery is performed on first request.
    if ($cachedItems.Count -gt 0) {
      Respond $ctx 200 (Json @{elements=$cachedItems;source='cache';center=@{lat=$lat;lon=$lon}}); continue
    }
    $ci=[Globalization.CultureInfo]::InvariantCulture
    $latStr=$lat.ToString($ci); $lonStr=$lon.ToString($ci)
    # More results and a wider radius for large cities, while still favoring central sights.
    $query='[out:json][timeout:15];(nwr(around:8000,'+$latStr+','+$lonStr+')[tourism~"attraction|museum|viewpoint|gallery|artwork|zoo|theme_park|information"][name];nwr(around:8000,'+$latStr+','+$lonStr+')[historic~"castle|monument|memorial|archaeological_site|ruins|building|church|yes"][name];nwr(around:6000,'+$latStr+','+$lonStr+')[amenity~"theatre|arts_centre|place_of_worship"][name];nwr(around:5000,'+$latStr+','+$lonStr+')[leisure~"park|garden"][name];);out center 100;'
    $encoded=[uri]::EscapeDataString($query)
    $foundOnline=$false
    foreach($endpoint in @('https://overpass-api.de/api/interpreter')) {
      try {
        $response=Invoke-RestMethod -Method Post -Uri $endpoint -Body @{data=$query} -Headers @{'User-Agent'='TravelPlannerPersonal/1.0'} -TimeoutSec 15
        $items=@(ValidTouristItems -inputItems @($response.elements) -cityLat $lat -cityLon $lon)
        if($items.Count -gt 0) {
          try {
            $saved=@{}
            if(Test-Path -LiteralPath $placesCacheFile) {
              $existing=Get-Content -LiteralPath $placesCacheFile -Raw -Encoding utf8 | ConvertFrom-Json
              foreach($prop in $existing.PSObject.Properties){$saved[$prop.Name]=$prop.Value}
            }
            $saved[$cacheKey]=$items
            $temp=$placesCacheFile+'.tmp'
            [IO.File]::WriteAllText($temp,(ConvertTo-Json -InputObject $saved -Depth 15 -Compress),[Text.UTF8Encoding]::new($false))
            Move-Item -LiteralPath $temp -Destination $placesCacheFile -Force
          } catch { Write-Warning ('Écriture cache : '+$_.Exception.Message) }
          Respond $ctx 200 (Json @{elements=$items;source='online';center=@{lat=$lat;lon=$lon}})
          $foundOnline=$true; break
        }
      } catch { Write-Warning ('Serveur touristique indisponible ('+$endpoint+') : '+$_.Exception.Message+' ; essai du serveur suivant.') }
    }
    if ($foundOnline) { continue }
    # Independent fallback: Wikipedia geosearch returns coordinates directly.
    # Unlike generator=geosearch, list=geosearch does not require prop=coordinates.
    try {
      $wikiUrl='https://fr.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord='+$latStr+'%7C'+$lonStr+'&gsradius=10000&gslimit=100&format=json'
      $wiki=Remote $wikiUrl
      $wikiItems=@()
      if ($null -ne $wiki -and $null -ne $wiki.query -and $null -ne $wiki.query.geosearch) {
        foreach($page in @($wiki.query.geosearch)) {
          if ($null -eq $page -or [string]::IsNullOrWhiteSpace([string]$page.title)) { continue }
          if ($null -eq $page.lat -or $null -eq $page.lon) { continue }
          if ([string]$page.title -match '(?i)^(Null Island|Bouée Soul|Liste des|Catégorie:|Modèle:|Fichier:|Discussion:)') { continue }
          $wikiItems+=@{type='node';lat=[double]$page.lat;lon=[double]$page.lon;tags=@{name=[string]$page.title;tourism='attraction';wikipedia=('fr:'+[string]$page.title)}}
        }
      }
      $wikiItems=@(ValidTouristItems -inputItems $wikiItems -cityLat $lat -cityLon $lon)
      if ($wikiItems.Count -gt 0) {
        try {
          $saved=@{}
          if(Test-Path -LiteralPath $placesCacheFile) {
            $existing=Get-Content -LiteralPath $placesCacheFile -Raw -Encoding utf8 | ConvertFrom-Json
            if ($null -ne $existing) { foreach($prop in $existing.PSObject.Properties){$saved[$prop.Name]=$prop.Value} }
          }
          $saved[$cacheKey]=$wikiItems
          $temp=$placesCacheFile+'.tmp'
          [IO.File]::WriteAllText($temp,(ConvertTo-Json -InputObject $saved -Depth 15 -Compress),[Text.UTF8Encoding]::new($false))
          Move-Item -LiteralPath $temp -Destination $placesCacheFile -Force
        } catch { Write-Warning ('Cache Wikipedia : '+$_.Exception.Message) }
        Respond $ctx 200 (Json @{elements=$wikiItems;source='wikipedia';center=@{lat=$lat;lon=$lon}})
        continue
      }
    } catch { Write-Warning ('Recherche touristique Wikipedia : '+$_.Exception.Message) }
    # Internet down or no OpenStreetMap data: curated catalog is a fallback.
    # Prioritize a reliable offline catalog for known cities; external services are optional.
    if (Test-Path -LiteralPath $localPlacesFile) {
      $catalog=Get-Content -LiteralPath $localPlacesFile -Raw -Encoding utf8 | ConvertFrom-Json
      $local=$catalog.PSObject.Properties[$city]
      if($null -ne $local -and @($local.Value).Count -gt 0) {
        $items=@($local.Value)
        $center=@{lat=[double]$items[0].lat;lon=[double]$items[0].lon}
        Respond $ctx 200 (Json @{elements=$items;source='local';center=$center}); continue
      }
    }
    Respond $ctx 200 (Json @{elements=@();source='unavailable'}); continue
   }
   if ($method -eq 'GET' -and $path -eq '/europe-cities.json') {
    Respond $ctx 200 ([IO.File]::ReadAllText((Join-Path $root 'data/europe-cities.json'),[Text.Encoding]::UTF8)); continue
   }
   if ($method -ne 'GET' -or $path -notin @('/','/index.html','/app.js','/v3.js','/v4.js','/style.css')) { Respond $ctx 404 '{"error":"Introuvable"}'; continue }
   $file=if ($path -eq '/') {'index.html'} else {$path.TrimStart('/')}
   $content=[IO.File]::ReadAllBytes((Join-Path $www $file))
   $ctx.Response.StatusCode=200; $ctx.Response.ContentType=switch ([IO.Path]::GetExtension($file)) {'.js' {'text/javascript; charset=utf-8'} '.css' {'text/css; charset=utf-8'} default {'text/html; charset=utf-8'}}
   $ctx.Response.ContentLength64=$content.Length; $ctx.Response.OutputStream.Write($content,0,$content.Length); $ctx.Response.Close()
  } catch {
   $message=$_.Exception.Message; Write-Warning $message
   try { Respond $ctx 400 (Json @{error=$message}) } catch { try {$ctx.Response.Close()}catch{} }
  }
 }
} finally { $listener.Stop(); $listener.Close() }
