# Guidance — verwerking stap voor stap

Bijgewerkt: 16 november 2026. **Inmiddels live en op expliciet gebruikersverzoek permanent geactiveerd.** Kaart en routeaanwijzingen zijn fysiek zichtbaar bevestigd; detailgedrag niet volledig fysiek afgetest. Zie CODEX_HANDOVER.md voor installatie en confirmed-markers.

De opdracht is gecorrigeerd naar: de werkende ontvangst- en uitvoerketen van guidance behouden, evenals kaart en zoom. Alleen inhoud/verwerking uitbreiden of corrigeren. Deze checklist is daarom geen toestemming om de resterende transport-, takeover-, menu- of eigen-rendererfuncties uit de bredere 68-regelige audit te vervangen.

| Stap | Verwerkingspunt | Lokaal resultaat | Bewijs / fysieke grens |
|---|---|---|---|
| 1 | Actuele manoeuvre + afstand | Afgewerkt en gecontroleerd | Bestaande cursor/prefetch/deltatests; extra count=0 trekt selectie terug zonder de payloadcache te wissen. Nieuwe lijst mag dezelfde payload hergebruiken. Geen toekomstige manoeuvre lenen. Fysieke routeproef nog nodig. |
| 2 | Rotondehoeken + kruispuntzijtakken | Geport en getest | Bestaande mapper 4536 gevallen; nieuwe `PorscheRouteGuidanceSideStreets` rechtstreeks uit LuKa-referentie, 29484 onafhankelijke vergelijkingsgevallen. Signed junction_angles/TLV0x0a nu doorgegeven naar bestaande BAP-descriptor. Geen pixeloffset/eigen renderer. |
| 3 | Fases, bargraph, tijdelijke afstand | Geport en getest | 1500/3000m en 15%-venster blijven; referentieblink laatste20%, 600ms100/0 via bestaande Java-poll (geen nieuwe thread). Afstandreplay uitsluitend dezelfde cursor/type; nieuwe cursor krijgt nooit oude afstand. Timing op echte teller onbevestigd. |
| 4 | Lane-events, richtingen, verbergen | Gecontroleerd/aangevuld | Cache van 8 naar32events, actieve event beschermd bij 39 nieuwere events; signed hoeken/side-directions en show/hide bestaande tests. Count/route-gate aangesloten. Volledige lane-completeness-/beschrijvingmetadata blijft niet identiek aan referentie; geen volledige apppariteit claimen. |
| 5 | Volgende straat, afrit, bestemming | Aangesloten en getest | Firmwarebewezen `setTurnToInfo(BapTurnToInfo[])` voor weg/signpost, apart van huidige positie; referentietekstnormalisatie/colon-prefix en UTF8-grens. Bestaande `setDestinationInfo`/BAP46 behoudt aankomstadres. Plaatsing op echte teller onbevestigd. |
| 6 | Reistijd / aankomsttijd | Aangesloten en getest | TLV5ETA en TLV6metbronmoment; absolute ETA, klok via `env.getFramework().getUTCTime()`, lokale conversie via `convertUTCTimeToLocalTime()`. Bestaande `setRgTimeToNextDestination(...,true,...)` gebruikt OEM12/24-uursinstelling. Expliciete aankomst maakt oude tijd ongeldig. Gecontroleerd met OEM-descriptors + testklok; geen echte tijdsweergave gezien. |
| 7 | Stoppen, aankomst en oude aanwijzingen | Aangevuld en getest | Native publiceert pending stop + originele deadlines; bestaande Java-poll laat 800msstop/5saankomst ook zonder volgend datapakket verlopen. Geen receive-thread/timer erbij. Appwissel/nieuwe route wist oude deadlines, velden worden afzonderlijk gewist met retry. Harde netwerk-/protocol-disconnectevents blijven de bestaande keten volgen. |

## Behouden grens

`tests/fixtures/guidance-processing-boundary.json` legt de beginhashes van 12 bestanden vast: bestaande ontvangsthook, kaart-/displaybeheer, sessiecode, capture/supervisorstarter, mm-ipod/HMI-starters, display-/zoom-Java en verified/v14-artifacts. Zowel test `tests/test_guidance_processing_boundary.py` als de checklist-pakketbuilder weigert afwijkingen. De guard is alleen na een apart beoordeelde scopewijziging bij te werken, nooit automatisch om een failure te verbergen.

De bestaande map- en eerdere guidance-ZIP zijn bytegelijk gebleven aan de checkpointkopie. Checkpoint: `build/guidance-processing-checkpoint/before-checklist.zip`. Dit is een lokale bewaring, geen nieuwe fysieke bewijsronde of vervanging van `verified/v14`.

## Implementatie

- `native/porsche_rgi.c/.h`: bestaande parser/cache en publicatie uitgebreid. `native/porsche_rgi_hook.c` niet gewijzigd.
- `java/de/audi/tghu/navi/app/cluster/PorscheRouteGuidance.java`: dezelfde listener/polllus, bestaande OEM-uitvoerfuncties.
- `PorscheRouteGuidanceSideStreets.java`: LuKa GPL3, commit `21f501611b0b28dbdeb2849e8443ce90ec9517ff`. Alleen package/classnamen en constantebinding aangepast; functionele berekening tegen originele Git-objecten getest. Zie `LICENSE.upstream`.
- `CWRG5`: nieuwe versie van uitsluitend de interne native/Java-snapshot, via hetzelfde atomische bestand/CRC. Bevat junctionhoeken, count, ETA/bronmoment, deadlinegegevens en afzonderlijke weg/signpost. Geen nieuw iAP2-bericht, netwerkendpoint, transportcallback of thread. Nieuwe Java leest ook CWRG1/2/3/4; oude Java leest CWRG5 niet, dus native/JAR altijd samen installeren.
- Firmware-inputherstel uitgebreid in `recover_destination_api.py`. Build controleert hashes van bestaande `BapTurnToInfo`, `NavigationEnv`, `IFrameworkAccess`, DestinationInfo-classes en de benodigde methodes/veldtoegang. Deze OEM-klassen NIET als vervanging in de JAR opgenomen.
- Guidance-split bevat één bestaande OEM-hook (`ClusterService`) en negen eigen guidanceclasses incl. side-helper/innerclasses. Display- en zoom-JARhashes zijn ongewijzigd.

## Controles die geslaagd zijn

- Volledige native ASan/UBSan-suite, inclusief 178 sessiechecks en nieuwe `test_guidance_processing.c`.
- 4536 mapper-oraclecases en 29484 sidestreet-oraclecases uit vastgezette referentie.
- QNX6.5ARM-crossbuild.
- Java/legacy-bytecodebuild en display-, zoom-, notificatie- en guidancefixtures.
- Echte native TLV -> echte CWRG5-publicatie -> Java-read -> gemockte bestaande OEM-listener, via `GuidanceNativeFixture`. Dit bewijst de softwareketen, geen fysieke MOST-/clusteracceptatie.
- 21 relevante Pythonchecks, 1 Windows shellfixture skipped (niet als passed tellen).
- QNX-toolchain-ksh syntaxiscontrole voor install/herstel.
- `guidance_package_transaction.py`: corrupte payload geweigerd vóór mount, gepaarde installatie/backup/herstel, markers teruggezet, kaartbestand ongewijzigd, RO-remount. Dit draait op een mockbestandssysteem, niet op de fysieke unit.

## Testpakket

`build/guidance-processing-checklist-MU1417.zip`

- ZIP SHA256: `6bbf751cae01f76b206cb289bf9a856925f253a9a328cd930b1ad48be9cf4402`.
- Native: `c917554dc9027d8d0fc8044dbccf71c1ef7f5689966427b7bf122df86701e2e9`.
- Guidance-JAR: `a24db7e9851b736bc4a3def7081de8219ab4f6e9f15a23c6ed644e1b5d30bf52`.
- Alleen native guidance-library, guidance-JAR, manifest, license, LEESMIJ, install/herstel. Geen kaart-, zoom-, starter- of menuvervanging.
- Exacte oorspronkelijke live guidancehashes vereist; onbekende uitgangstoestand wordt geweigerd. Backup `controls-v15/before-processing-checklist-20261116`.
- One-boot proef via reeds bestaande markers/wrappers; geen automatische reboot. Niet confirmed schrijven vóór een geslaagde fysieke proef.
- Inmiddels geïnstalleerd en beide confirmed-markers permanent geactiveerd op expliciet verzoek. Nog niet gecommit of gepusht.

Bouwen: `python build-tools/build_guidance_patch.py --profile checklist`. Eerst native en Java bouwen/splitsen. Gebruik niet per ongeluk het standaardprofiel om het bewaarde eerdere pakket te overschrijven.

## Nog te doen / niet als af voorstellen

1. Op een afgesproken moment fysieke test van de nieuwe verwerkingsversie: bestaande kaart blijft werken, twee opeenvolgende manoeuvres, rotonde, lanes, weg/signpost, ETA, aankomst/adres, stoppen en USB-reconnect.
2. De nieuwe uitkomsten op de echte Porsche kunnen nog afwijken van de softwarefixtures; geen garantie op foutloze fysieke werking gegeven.
3. Transportstop5203, backoff/verzendcontext, componentrouting, volledige generatie-/takeoverlogica en extra referentiemenu/scroll/eigen renderer zijn door de aangescherpte scope niet vervangen. Zie bredere portmatrix; dit is geen volledige 68-functiesport.
4. Huidige ontvangstketen behoudt ook haar bestaande risico's; de eerdere TX-/loaderproeven mogen niet via deze checklist terugkeren.


Latere live-aanvulling: op expliciet gebruikersverzoek ook het losse kaartfixpakket
geïnstalleerd (window41414ee5) en alleen de videosupervisor herstart. Runtime toont
CARPLAY_ACTIVE800x480; guidance/confirmedmarkeringen bleven aanwezig. Zie actuele
handover; deze deployment verandert de oorspronkelijke verwerkingsboundary niet.
Nieuwe koude-boot-/duurproef en fysieke kaartbevestiging na de omschakeling nog open.
