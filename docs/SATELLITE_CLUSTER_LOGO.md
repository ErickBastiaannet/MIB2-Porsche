# Origineel Google-logo op de satellietkaart van de teller

Onderzocht op 16 november 2026. Alleen lokale firmwareanalyse; geen unitwijziging.
Doel: onjuist oud Google-logo verwijderen wanneer alternatieve satellietbeelden
worden gebruikt, met behoud van correcte beeldleveranciervermelding.

## Bevestigd uit MU1417-bytecode

- `de/audi/tghu/navi/app/map/SatelliteMapsMediatorFSM.notifyClusterAboutSatMapsState(boolean)`
  haalt bij terminal0 de ClusterService op. Bij bevestigde satellietkaarten en geen
  providerwissel roept deze `ClusterService.updateMapView(1)` aan. De firmwaretekst
  daarbij luidt `sat maps confirmed - set logo`. Bij niet actief/bevestigd of
  providerwissel wordt `updateMapView(0)` gebruikt.
- `ClusterService.updateMapView(int)` roept `CombiBAPListener.setMapView(int)` aan.
  Die bewaart de waarde en publiceert via `CombiBAPServiceNavi.updateMapView(int,int)`.
  Dit is een afzonderlijke berichtketen naar de teller, geen satelliet-JPEGbewerking.
- `RenderingInfoProvider.SatelliteMapsLogoConstants` onderscheidt main style204
  en combi style206, met resources1610612753 en1610612755. Een ontvangen combilogo
  activeert in `updateSatelliteMapsLogos(int)` bovengenoemde clusterberichtketen.
- Native `libPresentationController.so` heeft afzonderlijke MainUnit- en
  ClusterInstrument-logoaanvragen; `providerlogos.db` ligt onder
  `/mnt/gecache/ebnav/`. De downloader gebruikt `1.0/sat/logo/...`.
- `SatelliteMapsGUI.kombiMapCopyRightLogoPosition` positioneert apart het
  copyrightgebied. Dit is NIET automatisch de juiste plaats om alleen het
  oude Google-logo te verwijderen: leverancierstekst moet behouden blijven.
- Het eerder gevonden `eso/hmi/lsd/images/AppNavi/logo_map.png` wordt vanuit
  `OnlineSearchProviderHandler` gebruikt, ook met overridepad
  `/var/app/ols/providericons/logo_map.png`. Deze POI-resource niet blind vervangen.
- `DSIMapViewerControl.setBrandIconStyle` betreft volgens native trace
  branded POIs; niet als bewezen schakelaar voor het satellietlogo gebruiken.

## Waarschijnlijke verklaring, nog fysiek te bewijzen

De teller voegt bij MapView=1 zelf de oude Google-branding toe. Dit past bij
gebruikersobservatie dat het logo boven het kleurenbalkentestbeeld bleef staan
en verdween bij satellietweergave uitschakelen. Nog geen bewijs dat het logo
een eigen vrij manipuleerbare displaymanagerlaag is. De oude displayable58
DISPLAYABLE_GOOGLE_EARTH_KOMBI_MAP_VIEW is geen bewezen logo-only-laag.

## Volgende gerichte proef

Bepaal eerst de exacte BAP MapView-functie/serializer en effecten op deze teller.
Test daarna, afzonderlijk en omkeerbaar, de logo/MapView-melding zonder de
satellietsetup of beeldstroom te wijzigen. Observeer of MapView0 uitsluitend
logo verwijdert of ook tellerfuncties/weergave verandert. Geen globale
satellietuitschakeling, geen copyrightverwijdering en geen blinde Java-hook.
De werkende CarPlay/guidance- en startupketen moet intact blijven.

## Analysebestanden

Teruggewonnen classes en javap-output: `.tmp/logo-research/` (niet in Git).
Bron-ROM: `mqb-backend-private/.tmp/porsche-carplay-mu1417/rom.classes`;
gelezen via bestaande jxe2jar-parser. Exacte geanalyseerde classhashes:

- `de/audi/app/navi/pgen2/map/SatelliteMapsGUI.class`: `ab386e2713c7fed5c5cc67e6cf103cf4ec8ff5e2a4f27e95d8d53230bf3cceda`

- `de/audi/atip/interapp/icon/RenderingInfoProvider$SatelliteMapsLogoConstants.class`: `48881f26835b5ac4ee5355c15837f914b22e9dc81cf1a194965cd682afcf6787`

- `de/audi/tghu/navi/app/map/SatelliteMapsMediatorFSM.class`: `4f02d31330c0be9ab5038329ff3a7aedd52cf8cc91da3d4571f8b6b2de8bdb2f`


## Fysieke proefuitslag

16 november 2026: gebruiker bevestigde `CarPlay-kaart zonder Google-logo` voor
proef-JAR59842f9e68060680a93dcbb2eba6dbeb184dfd1295a626782b832c9905bcf542.
Originele satellietweergave moest bij deze proef aan blijven. BAP-filter registreerde
MapView0 tijdens geldige CarPlay-readylease. Dit bevestigt de onderzochte route
voor onderdrukken. Herstel naar originele satellietkaart en reconnect nog niet
fysiek bevestigd. Proef blijft one-boot; geen permanente activatie uitgevoerd.


## Permanente activering

Na expliciete gebruikersopdracht permanent bevestigd op 16 november 2026.
Zie bovenste actuele sectie in CODEX_HANDOVER.md voor live hashes, generator,
back-ups en resterende fysieke checks. Runtime-transities view0/true -> view1/false
-> view0/true gezien. Geen extra reboot gedaan. Vorige one-boot-status hierboven
is historisch en niet meer de actuele configuratie.
