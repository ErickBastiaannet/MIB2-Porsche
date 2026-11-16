# Guidancecontrole tegen de referentie — bijgewerkt 16 november 2026

**Actuele beperking (16 november):** live transportproeven zijn teruggetrokken.
De laatste TX-callback stuurde 5200 met rc=0 maar CarPlay viel ook op de PCM uit.
De precieze oorzaak is niet vastgesteld. De gebruiker heeft verdere liveproeven
stopgezet. De oorspronkelijke guidance-/videobestanden en confirmed-markers zijn
teruggezet op schijf, zonder daaropvolgende herstart of fysieke verificatie.

De smallere lokale kandidaat behoudt transport van commit `288175f`; alleen
passieve lifecycle-expiratie is toegevoegd. Geen nieuwe TX-hook of threads.
Parser-/presentatiecorrecties hieronder zijn lokaal getest, niet fysiek bewezen.
Het oorspronkelijke synchrone verzendpad blijft daarmee ook bestaan; dit is geen
bewijs dat dit pad altijd stabiel is. Zie `CODEX_HANDOVER.md` voor exacte status,
hashes en het afzonderlijke guidance-pakket. Niet opnieuw breed live installeren.

## Bronnen en grens van de controle

Referentie: `https://github.com/luka-dev/mib2q-carplay-rgi`, vastgezet op
`21f501611b0b28dbdeb2849e8443ce90ec9517ff`. De lokale checkout staat in
`.tmp/mib2q-carplay-rgi`. Betrokken referentiecode is van LuKa en valt onder
GPL-3.0; zie ook de bestaande `LICENSE.upstream`. Geen nieuwe renderer of
referentie-HMI voor een andere firmware installeren.

Aanvullende vergelijking: de lokale Fifthbro MH2P-bron onder
`build/refs/fifthbro-mh2p-cluster/.../CarPlayClusterIntegration.java`, methode
`getManeuverStateForDistance`. Die gebruikt vier afstandszones; de onderstaande
implementatie volgt bewust één beleid, dat van de vastgezette MIB2-referentie,
en mengt die drempels niet met Fifthbro-configuratie.

Firmwarecontrole: `build/CombiBAPListener.javap.txt`, afkomstig van de exact
gehashte MU1417-klasse, bevestigt `updateBapManeuverState(int)` met waarden 0..4.
`NavLaneGuidanceData` geeft positie, BAP-richting en extra richtingen via de
bestaande OEM-omzetting door. Deze koppelingen veranderen de schermlayout niet.

## Gevonden afwijkingen en correcties

| Onderdeel | Referentie | Correctie in dit project |
| --- | --- | --- |
| Actuele manoeuvre | `ManeuverPresentation.currentSlot`: eerste entry van `maneuverOrder` | `native/porsche_rgi.c` leest eerste uint16 van TLV 0x0d, niet de tweede |
| Vooruitgestuurde instructies | `rgd_hook.c`: cache, geen promotie van toekomstige entry bij ontbrekend huidig payload | Alleen de actuele cursor mag de descriptor wijzigen; lege/missende lijsten onderscheiden |
| Lange routes | Cache slots met volledige iAP2-identiteit | 64 begrensde slots met uint16-ID; actuele entry beschermd tegen verdringing |
| Deltaberichten | `rgd_tlv.c`, `rgd_hook.c`: afwezige velden behouden | 0x5202 wist geen bestaande tekst, hoek of type; activeert route niet zelfstandig |
| Afstand | `BAPBridge.update`: primaire identiteit begrenst afstandscache | Cursorwissel invalideert oude afstand vóór verwerking van nieuwe TLV's; ontvangen TLV-volgorde verandert het resultaat niet |
| Symbolen | `ManeuverMapper.map`, incl. hoekaanwezigheid, junction-gate en verkeerszijde | 4.536 onafhankelijke referentiegevallen; eerdere afwijkingen in rotondehoek, oprit/afrit, aankomstzijde en U-bochten gecorrigeerd |
| Rijstrookevents | `rgd_hook.c`, `BAPBridge.activeLaneSlot` | Acht cache-events met uint16-ID; route-index kiest event; nieuw vooruitgestuurd event overschrijft het actuele niet |
| Zichtbaarheid rijstroken | `BAPBridge.laneGuidanceVisible`: expliciet showing | Alleen wirewaarde 2 (=expliciet zichtbaar) activeert de OEM-rijstrookfunctie; onbekend is verborgen |
| Rijstrookgeometrie | `BAPBridge.mapRawLaneValueToDirectionCode`, `mapLaneSideStreets`, `mapGuidanceInfo` | Signed graden naar BAP-code; extra richtingen gesorteerd/ontdubbeld; onbekende geometrie niet verzinnen of aanbevelen |
| Volgen/voorbereiden/actie | `BAPBridge.update` en `getBargraphDenominatorM` | Bestaande Porsche `updateBapManeuverState`, normale procentwaarde 0..100; niet voortdurend een 0..255-actiebargraph over 1 km |
| Appbron | sourceName kan later dan payloads aankomen | Eerste bronlabel behoudt eerder ontvangen sessiegegevens; echte appwissel wist oude gegevens |

## Bestemmingsadres en aankomst — concrete ontbrekende koppeling hersteld

De vastgezette referentie `BAPBridge.java` publiceert in blok 9 (FctID 46)
`CombiBAPDestinationInfo(new CombiBAPNaviDestination("", "", dest, "", "", "", ""))`,
met `dest = limitUtf8(destination, 50)`. Deze publicatie ontbrak bij ons.
Het functienummer is ook rechtstreeks in MU1417 bevestigd, niet alleen in de
referentie: `AppConnectorNavi.updateDestinationInfo` haalt met `bipush 46`
`getBAPFunctionPropertyFSG(46)` op en maakt `DestinationInfo_Status` aan.
`DestinationInfo_Status.functionId()` retourneert eveneens 46.
Bewijs: `build/destination-wire.javap.txt` (rond 1937 en 4757), uit originele
ROM geconverteerd. Classhashes: AppConnectorNavi
`d836dd120f7363ec92bcb437c123d01ba8c7cc137e64f13d6791e1a57bd9b032`,
DestinationInfo_Status `3b58e37c47ffd38715af5ff5b7b733c09d837ead0a039fdbdefaa46dc79cdada`.
Deze classes zijn alleen geanalyseerd en niet gepatcht of meegeleverd.

MU1417 heeft exact `CombiBAPListener.setDestinationInfo(...)` en beide constructors;
ze zijn uit de originele ROM hersteld, gehasht en door de build op descriptor gecontroleerd.
`PorscheRouteGuidance` gebruikt nu dat OEM-pad, bewaart het label bij aankomst en wist
het bij beëindiging. De fixture draait met de herstelde OEM-dataklassen en controleert
ook UTF-8-grenzen, retry bij clearfout en behoud van de huidige straat.

De referentie gebruikt daarnaast CurrentPositionInfo voor wisselende routetekst.
Dat deel nemen we niet blind over: de gebruiker heeft uitdrukkelijk gemeld dat
volgende straat/adres de daadwerkelijke huidige positie niet mag overschrijven.
DestinationInfo blijft daarom een afzonderlijk veld. De uiteindelijke plaats van
het adres op het echte Porsche-scherm is nog niet fysiek bevestigd.

## Een pijl op 900 meter

De referentie heeft twee presentatiemodi voor verre manoeuvres: **Next**
(standaard: volgende actuele instructie alvast tonen) en **Straight** (buiten
de voorbereidingszone de weg volgen). Dit is geen tijdschema dat iedere paar
seconden naar een volgende pijl springt.

Het standaardbeleid is behouden:

- Lokaal: voorbereidingszone 1.500 m; snelweg: 3.000 m.
- Een ontvangen staplengte boven 2.000 m kiest de snelwegzone; zonder staplengte
  gebruikt de referentie de categorie oprit/afrit/snelwegwissel als fallback.
- Actiebargraph: 15% van de voorbereidingszone (225/450 m), begrensd door een
  kortere bekende staplengte. Buiten die zone geen actiebargraph.
- Geen bruikbare actuele manoeuvre: `FOLLOW_STREET`, geen geleende toekomstige
  pijl. Een lege lijst is een echte clear; een ontbrekende lijst behoudt state.
- Op 900 m kan dus een voorbereidingspijl terecht zijn. De volgende aanwijzing
  mag niet verschijnen alleen omdat haar payload ontvangen is. Er is geen
  zelfbedachte wachttijd na iedere bocht.

De referentieoptie Straight is beschikbaar via de Java-property
`connectwow.carplay.guidanceFarStraight=true`; standaard blijft die false,
zoals `RGI_FAR_DEFAULT = RGI_FAR_NEXT` in de referentie. Geen nieuwe unit- of
menustelling is hiervoor aangebracht.

## Pijlpositie: originele BAP-teller versus eigen renderer

`BAPBridge.sendManeuvers` gebruikt voor de originele teller een descriptor met
`main`, `direction`, `z` en `sideStreets`. `sendLaneGuidance` levert afzonderlijk
de lane-posities en -richtingen. Dit pad heeft geen pixel-X/Y of appafhankelijke
uitlijningsparameter. De Porsche-port volgt dat pad; zijn firmware bepaalt de
plaatsing. De eerder doorgestuurde graden als BAP-code en onbekende zichtbaarheid
zijn echte afwijkingen in die invoer, geen bewijs van een benodigde pixeloffset.

De referentie bevat daarnaast `maneuver_render/render.c` met onder meer
`g_cam_pan_x`, `g_content_offset` en `render_set_content_framing`. Dat positioneert
een zelf getekende OpenGL-scene. Die waarden zijn geen stuurvelden voor de
originele Porsche-tellerpijl en worden daarom niet in de BAP-port gekopieerd.

`test_app_independent_presentation` in `tests/test_rgi.c` speelt dezelfde actuele
manoeuvre, afstand en rijstrookevent af voor Apple Maps en Google Maps. De gehele
uitvoerstaat moet identiek zijn op het diagnostische appbronlabel na. Dit sluit
appspecifieke positionering in onze verwerking uit voor die invoer; het bewijst
niet dat twee apps op straat werkelijk identieke instructies leveren of dat de
fysieke teller met de gecorrigeerde invoer al is waargenomen.

## Protocol en installatie-eenheid

**CWRG4** voegt aan de CWRG3-velden (type, staplengte, afstandsgeldigheid en
actuele cursor) route_state en end_reason toe. Rijstrooktokens kunnen na `;`
de volledige reeks uint16-hoeken in hex bevatten. Java accepteert ook
CWRG1/CWRG2/CWRG3.

De **native RGI-library en guidance-JAR moeten samen bijgewerkt worden**.
Een oude Java-JAR accepteert CWRG4 niet. Verander geen renderer, display-JAR,
zoom-JAR, starters of notificatie-JAR voor deze correctie. De geverifieerde
build controleert de extra interne `Presentation`-klasse ook in de split-JAR.

## Stoppen, aankomst en sessiewissels

| Gebeurtenis | Gedrag en bron |
| --- | --- |
| Gewone RS=0 | Referentie `rgd_hook.c`: 800 ms wachten op actieve vervolgdata, daarna alle routegegevens wissen; herhaalde nullen verlengen dit niet |
| RS=5 -> RS=0 | Reroute-reset blijft pending zonder eigen zero-timeout, zoals de referentie; geldige vervolgdata maakt een schone routegeneratie |
| source_supports_rg=0 | Direct hard-clear; geen reroute- of aankomstvertraging |
| Expliciete RS=2 | Bereikt-pictogram tonen, lanes/progressie uit; na vijf seconden wissen, volgens Fifthbro `stopRouteGuidance` / `destinationDisplayDuration` |
| Vooruitgestuurd aankomstpayload | Fifthbro `ARRIVAL_ICON_THRESHOLD_M=70`: geen bereikt-weergave op 900m alleen omdat die manoeuvre al bekend is |
| Herhaalde aankomst/volgende RS=0 | Geen nieuwe vijfsecondenperiode; geen eerdere clear die de aankomstmelding meteen wegneemt |
| Nieuwe app/route | Oude arrival/stop-deadline en routecaches vervallen; vorige route-ID's mogen niet herleven |
| Nieuwe Identify/afwijzing/unload | Identify-start publiceert reset, unload publiceert inactief. Rejected zet in huidige hook alleen identified=0; directe event-clear niet volledig aangesloten. Niet gelijk aan volledige referentie-lifecycle |
| Proces abrupt weg/stille verbinding | Bestaande freshness/read-grace wist Java-guidance; zonder fysiek disconnect-event is dat geen onmiddellijke detectie |

Native deadlines lopen via `CLOCK_MONOTONIC`. In de huidige smallere kandidaat
wordt `cw_rgi_tick` uitsluitend op bestaande RX-traffic aangeroepen. Er is GEEN
lifecycle-worker of nieuwe mutex/thread. Zonder vervolgtraffic bepaalt de Java
freshness/read-grace de uiteindelijke clear; exacte 800ms/5s is dan niet gegarandeerd.
De eerdere tekst die een zelfstandige worker beschreef, betrof de verworpen proef.

Java-clear behandelt iedere OEM-aanroep apart en probeert na een fout opnieuw.
Het wissen betreft routevelden, geen originele huidige-positietekst. Zie
`tests/test_rgi_lifecycle.c` en de foutinjectie in `RouteGuidanceTextFixture.java`.

## Reproduceerbare controles

- `tests/test_rgi.c`: selectie, prefetch, lege/ongeldige lijsten, late payloads,
  eventselectie, ID 720, cacheverdringing en gedeeltelijke updates.
- `tests/test_rgi_mapping.c` + `tests/fixtures/rgi-map-reference.tsv`: 54 types,
  14 hoeken, drie junctionwaarden en twee verkeerszijden = 4.536 vectoren.
  Het verwachte resultaat is uitgevoerd door de vastgezette Java-referentie,
  niet gekopieerd uit onze C-mapper.
- `build-tools/export_reference_mapping.py REFERENCE --jdk JDK_BIN` herbouwt
  de fixture vanuit het vastgezette Git-object; weigert een andere revisie.
- `tests/run_native.sh`: bestaande native suite plus bovenstaande tests,
  met ASan/UBSan. Compilerinclude voor de bestaande reconnect-constructor
  is ook voor capture/listener-fixtures expliciet gemaakt.
- `tests/RouteGuidanceTextFixture.java`: CWRG1/2/3-contracten, OEM-aanroep,
  afstandsfases, bargraph, zichtbaarheid, signed lanehoeken en extra richtingen.
- `build-tools/build.py`, `split_hmi_bridge.py` en `build_qnx.sh`: OEM-hashes,
  bytecode, klasse-inhoud en QNX ARM-build.

## Nog fysiek te bevestigen

Deze controles bewijzen geen acceptatie of juiste timing op de echte teller.
De bestaande verschoven Apple-manoeuvrepijl kan samenhangen met ongeldige
rijstrookrichting of onterechte zichtbaarheid; de werkelijke schermpositie is
nog niet opnieuw waargenomen. Geen x/y-correctie gedaan.

Gerichte fysieke test: dezelfde route in Apple Kaarten en Google Maps, met
opname van actuele manoeuvre-ID, afstand, fase en lane-event rond minstens
twee opeenvolgende bochten en een rijstrookevent. Controleer ook route stoppen,
herberekenen, appwissel en USB-reconnect. De nieuwe artifacts zijn lokaal;
de unit en de SD-kaart zijn tijdens dit onderzoek niet veranderd.

## Volledige actuele portmatrix

Zie [GUIDANCE_PORT_MATRIX.md](GUIDANCE_PORT_MATRIX.md) voor de systematische
vergelijking van protocol, parser, manoeuvres, lanes, teksten, bestemming/ETA,
lifecycle, transport, uitvoer en optionele rendererfuncties. Deze bredere audit
maakt beperkingen expliciet die de eerdere mappergerichte beschrijving niet
dekte: onder andere ontbrekende junction-zijtakken, ETA, actionblink en niet
aangesloten 5203. Aanwezig in parser is niet automatisch end-to-end geport.
