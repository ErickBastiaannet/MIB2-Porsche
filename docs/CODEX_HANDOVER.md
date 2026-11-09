# Actuele Codex-overdracht — Porsche CarPlay-cluster

Laatst bijgewerkt: 9 november 2026

Repository: `D:\Software Development\Github\porsche-carplay`

Basis vóór deze overdrachtscommit: `main` / `765403c`
Doelfirmware: `MHI2_ER_POG24_K5137_MU1417_971919360T`

## Fysieke V15- en zoombevestiging — 9 november 2026

- **Fysiek bevestigd:** V15 bereikt op de Panamera `CARPLAY_ACTIVE display=1 context=70 size=800x480`; CarPlay-kaartbeeld en één zoomopdracht per encoderstap werken.
- De cold-startchurn kwam aantoonbaar door een te korte eerste-pixeltermijn: workers eindigden met `CARPLAY_RENDERER_EXIT pixel-timeout` voordat MU1417 het eerste bruikbare frame leverde. Alleen het eerste frame krijgt nu maximaal 15 seconden; na de eerste render blijft de fail-safe 5 seconden.
- Een live NvSS-configrefresh wordt niet meer destructief gesloten. MU1417 crashte daarbij in `libnvcwm.so` / `NvCwmServerPostMessage`; een echte decodeerfout blijft de geïsoleerde worker laten herstarten.
- Permanente V15-binary op de unit: SHA-256 `2fbc77417bb6f8d3258aff85418a4dc8e22edc2afe538d0c3a77376af11750a6`. De voorafgaande V15 is bewaard als `cw-window-candidate.pre-pixel-grace`.
- **Fysiek bevestigd:** de losse zoom-JAR werd via `-Xbootclasspath/p:` geladen en zoomt Apple CarPlay daadwerkelijk. De proef is na bevestiging permanent gemaakt met `/mnt/persist/connectwow-carplay/zoom-probe/confirmed`.
- Permanente HMI-launcher op de unit: SHA-256 `8aa790f9ad9c48c87db023397f7dc5fb5da71f35c6cebf7513783fc09e5a057d`. De launcher behoudt daarnaast de one-shot `pending` → `attempted`-route voor toekomstige onbevestigde proeven.
- **Bekende cosmetische beperking:** de teller toont tijdens CarPlay-zoom permanent de laatst geldige Porsche-schaal (waargenomen: 150 m). Dit is niet de werkelijke CarPlay-schaal. De waarde wordt bewust niet via de verborgen OEM-kaartcontext verhoogd, omdat dat eerder `---` en `unavailable` veroorzaakte. Functioneel zoomen werkt wel en de gebruiker heeft deze toestand geaccepteerd.
- Navigatie, browser, mediaonline en GEMIB draaiden na installatie. `/mnt/app` is na iedere transactie weer read-only gemount.

Lees eerst `../AGENTS.md` voor blijvende architectuur-, code-, build-, test- en veiligheidsregels. Dit document bevat de actuele status, dirty tree, open problemen en vervolgstappen.

## Hervattingscontrole ? 4 november 2026

- Werk uitgevoerd vanuit de voorgeschreven repository op D:. Bij aanvang waren werkboom en index schoon; `git diff` was leeg. Na `git fetch origin` stonden `main` en `origin/main` beide op `d572ce6`.
- De hieronder beschreven dirty tree is historisch: deze wijzigingen, inclusief de transferhelper, zijn vastgelegd in `234f63d`. De vervolgstap om die wijzigingen veilig te stellen is daarmee uitgevoerd.
- Verificatie van `d572ce6` gebeurde in een tijdelijke bronkopie; bestaande lokale buildartifacts zijn behouden. Java-build, bytecodecontrole, notification/guidance/cluster/zoom-fixtures en het splitsen van de JARs slaagden.
- QNX 6.5 ARM EABI5-build en aanvullende native tests met ASan/UBSan slaagden. Windows-CRLF in de tijdelijke shellscripts is v??r uitvoering naar LF omgezet. De native sessietest vereist daarnaast het bestaande gegenereerde `build/geometry.record` als fixture.
- Volledige Linux-suite na bouwen van host-runtimefixtures: **54 passed in 69.00s**. Aanvankelijk ontbraken pakket- en runtimefixtures in de tijdelijke kopie; dat was geen geslaagde volledige testrun.
- Het opnieuw gebouwde profielpakket heeft opnieuw SHA-256 `3c3e83229784d633d22514390e07e27e4652e1256d7c1593e1e449a752416afc`. Stable V14 bevat exact de bewezen renderer; Controls V15 bevat exact de opnieuw gebouwde renderer met SHA-256 `a73d7263559dfacca1fdff077ad49eb50aef9642107f48da97afd61f55419891`.
- Gebruikte Java-inputs staan onder `D:/Software Development/Github/mqb-backend-private/.tmp/porsche-carplay-mu1417/`: `porsche-carplay-selected.jar`, `porsche-display-selected.jar` en `toolchain/zulu17.70.111-ca-jdk17.0.21-win_x64/bin`. De build controleerde de vereiste OEM-classhashes.
- Er is niets naar de unit of SD gedeployed en er is geen nieuwe fysieke validatie uitgevoerd. Eerstvolgende prioriteit blijft native V15 cold-start met OEM-HMI; de gecombineerde Java-bridge blijft uitgeschakeld.

## 1. Bewijslabels

- **Bevestigd**: fysiek op de Panamera vastgesteld of rechtstreeks uit actuele code/build/testuitvoer vastgesteld.
- **Afgeleid**: ondersteund door firmwarebytecode, protocolanalyse of referentiecode, maar nog niet fysiek bevestigd.
- **Plan**: nog uit te voeren.

## 2. Huidige toestand

### Fysiek bewezen basis

**Bevestigd.** Stable V14 toont CarPlay-video op het rechter instrumentenscherm:

- 800 × 480;
- displaymanager report/index 1;
- backend display-ID 4;
- context 70;
- displayable 78;
- IPv6 CarPlay op TCP 7001;
- Apple Maps en Google Maps zijn in succesvolle proeven zichtbaar geweest;
- ongeldig/weggevallen beeld kan terugvallen naar de originele Porsche-kaart.

De bewezen binaries staan onder `verified/v14/`. Onderbouwing en hashes staan in `PHYSICAL-BASELINE.md`, `firmware-profile.json` en `verified-window-profile.json`.

### Actuele ontwikkeling

**Bevestigd.** Native Controls V15, zoom/autozoom-Java en uitgebreide RGI-code zijn lokaal gebouwd. De laatste volledige Linux-run gaf **54 passed** en de QNX 6.5 ARM EABI5-build slaagde.

**Bevestigd.** `install-controls` activeert momenteel alleen native V15 en houdt `lsd.sh.cw-stock` actief. De gecombineerde Java-bridge zit in het pakket, maar wordt niet geladen. Zoom, guidance en nav-ignore zijn dus niet automatisch actief door alleen Controls V15 te installeren.

**Bevestigd.** Actueel pakket:

- `build/porsche-carplay-profiles-MU1417.zip`
- SHA-256 `3c3e83229784d633d22514390e07e27e4652e1256d7c1593e1e449a752416afc`
- metadata: `build/profile-package.json`

Dit pakket is gebouwd uit een dirty tree en nog niet fysiek gevalideerd.

## 3. Recente wijzigingen

### Zoom

**Bevestigd uit code/tests.** `PorscheClusterControls` verstuurt weer één semantische opdracht per ontvangen MapScale-stap. Factoren twee en drie zijn verwijderd.

**Bevestigd uit firmwarebytecode.** Stock `CombiBAPListener.setMapScale(int)` doet `activeContext.increment(400476, steps)` en daarna `updateMapScale()`.

**Bevestigd uit actuele hook.** `BuildPorscheHooks` roept `consumeMapScale(steps)` aan maar laat vervolgens de volledige stockmethode doorlopen. Daardoor hoort de verborgen Porsche-schaal niet meer kunstmatig op 100 m te blijven staan.

**Nog fysiek te verifiëren.** Eén klik, draairichting, responstijd en veranderende schaal.

### Autozoom/hercentreren

**Bevestigd uit code/tests.** `consumeMapScaleSetting(int)` stuurt gedebounced `show-map` naar UDP-loopbackpoort 7032. De native receiver vertaalt dit naar CarPlay `showUI` met de cluster-UUID.

**Afgeleid.** Dit brengt de actieve CarPlay-kaart terug in beeld. Het is geen bewezen universele resetZoom/autozoomopdracht.

**Open.** De hook behandelt nu alle settingwaarden als `showUI`. Firmwarebytecode kent waarden 0, 1, 2 en 15. Fysiek vaststellen welke bediening/waarde gewenst is.

### Route Guidance

**Bevestigd uit code/tests.** De dirty tree bevat uitbreidingen voor manoeuvremapping, adaptieve afstandsupdates, heartbeat, straat/volgende weg, resterende afstand/tijd, lanes, arrival hold, nette clear, bounds, CRC, freshness en logging.

Relevante bestanden:

- `native/porsche_rgi.c`
- `native/porsche_rgi.h`
- `java/de/audi/tghu/navi/app/cluster/PorscheRouteGuidance.java`
- `tests/test_rgi.c`
- `tests/RouteGuidanceTextFixture.java`

**Nog niet fysiek bevestigd.** Pijlen, straattekst, lanes en remaining time/distance tijdens een echte route.

### Cold-start/preflight

**Bevestigde fysieke waarneming.** Eerst verscheen `CARPLAY_DISPLAY_PREFLIGHT_FAILED`, daarna volgden twee workerherstarts voordat `CARPLAY_ACTIVE` werd bereikt.

**Afgeleide oorzaak.** De supervisor reageerde op de eerste geldige geometrie terwijl owner en displaymanagercontext tijdens cold boot nog verschoven.

**Bevestigd uit actuele code.** `native/porsche_unit.c` vereist nu 1,2 seconde dezelfde owner en geometriesessie vóór de eerste workerstart. Nieuw logevent: `CARPLAY_SOURCE_STABILIZING`.

**Bevestigd uit packaging.** Controls V15 gebruikt nu `build/qnx/porsche-carplay-window-candidate`; Stable V14 blijft de bewezen binary gebruiken. Zonder deze wijziging zat de fix niet in V15.

**Nog niet fysiek bevestigd.** Of dit de dubbele start werkelijk oplost.

### Transferhelper

**Bevestigd.** `build-tools/telnet_push.py` is nieuw en nog niet gecommit. Het is bedoeld voor gecontroleerde staging naar de unit.

## 4. Werkboomstatus

Reset deze wijzigingen niet.

Gewijzigd:

- `README.txt`
- `build-tools/BuildPorscheHooks.java`
- `build-tools/build.py`
- `build-tools/build_profile_sd_zip.py`
- `build-tools/prepare_native.py`
- `java/de/audi/tghu/navi/app/cluster/PorscheRouteGuidance.java`
- `java/org/connectwow/carplay/PorscheClusterControls.java`
- `native/porsche_rgi.c`
- `native/porsche_rgi.h`
- `native/porsche_unit.c`
- `tests/ControlsFixture.java`
- `tests/RouteGuidanceTextFixture.java`
- `tests/test_rgi.c`

Nieuw:

- `build-tools/telnet_push.py`
- `AGENTS.md`
- `docs/CODEX_HANDOVER.md`

De wijzigingen omvatten meerdere onderwerpen. Review ze inhoudelijk voordat commits worden gesplitst.

## 5. Profielstatus

- **Stable V14 — bevestigd:** fysiek bewezen native basis en hersteloptie.
- **V14.5 — niet productiebewezen:** Online Menu/HMI toonde eerder alleen puntjes of liep vast; start was niet altijd stabiel.
- **V14.6 — onbevestigd:** notification-JAR plus one-shot/confirmable HMI-wrapper.
- **Controls V15 — deels bevestigd:** actuele native en Java-payload aanwezig, maar installer houdt Java bewust uitgeschakeld.

Open ontwerpbeslissing: voeg afzonderlijke one-shot Online Menu-acties toe voor split-JARs; activeer niet direct de gecombineerde bridge.

### Openstaande fysieke JAR-tests

Geen van onderstaande experimentele HMI-JARs mag direct permanent of gecombineerd worden geactiveerd. Iedere test vereist een afzonderlijke one-shot wrapper, automatische OEM-HMI-terugval op de volgende boot en expliciete bevestiging nadat navigatie normaal is gestart.

| JAR | Functie | Huidige bewijsstatus | Eerstvolgende fysieke test |
| --- | --- | --- | --- |
| `PorscheCarPlayZoom.experimental.jar` | Porsche MapScale naar CarPlay-zoom; stock schaal/ACK; autozoom naar `showUI` | Bytecode en fixtures slagen; laatste correcties niet fysiek bevestigd | Als eerste testen: navigatiestart, één stap per klik, richting, zichtbare schaal, reverse queue, autozoom en OEM-fallback |
| `PorscheCarPlayGuidance.experimental.jar` | RGI naar pijlen, afstand, straattekst, remaining time/distance en lanes | Native/Java-fixtures slagen; geen echte routeproef | Eerst met gecontroleerde state, daarna Apple Maps-route; aankomst en disconnect moeten netjes clearen |
| `PorscheCarPlayNavIgnore.experimental.jar` | Neutraliseert CarPlay-navigatie-eigendom zonder popup/speech te blokkeren | Statisch/lokaal gecontroleerd; niet afzonderlijk fysiek bewezen | Controleren dat OEM-navigatie niet wordt verdrongen en toegestane CarPlay-meldingen blijven verschijnen |
| `PorscheCarPlayNotifications.experimental.jar` | Notification/AppState-compatibiliteit voor V14.6 | Gebouwd en als one-shot voorzien; V14.6 niet volledig fysiek bewezen | WhatsApp/Telegram/andere toegestane iOS-melding testen met actieve CarPlay, plus boot en fallback |
| `PorscheCarPlayDisplay.experimental.jar` | Contextinstallatie, clusterdisplayrouting en CarPlay-displaystatus | Native displaypad is bewezen; Java-displayhook niet geïsoleerd bewezen en heeft de hoogste bootimpact | Als laatste testen: cold boot, contextwissel, reconnect, zwartbeeldfallback en normale OEM-kaart |
| `PorscheCarPlayBridge.experimental.jar` | Gecombineerde bridge met meerdere hooks | Mag niet als eerste test worden gebruikt; eerdere gecombineerde injectie blokkeerde navigatiestart | Pas testen nadat alle bovenstaande onderdelen afzonderlijk dezelfde boot/reconnect/herstelcriteria hebben doorstaan |

De splitinhoud en actuele hashes staan in `build/split-hmi-manifest.json`. `PorscheCarPlayNotifications.experimental.jar` wordt apart door `build-tools/build.py` gebouwd en staat daarom niet in die splitmanifesttabel.

## 6. Bekende bugs en risico's

1. Gecombineerde Java-injectie heeft eerder navigatiestart geblokkeerd; de veroorzakende hook is nog niet geïsoleerd.
2. Cold start is nog onbewezen na de 1,2-seconde stabilisatie.
3. Zoom en autozoom zijn lokaal gecorrigeerd maar niet fysiek herbevestigd.
4. Autozoom→`showUI` kan te breed gekoppeld zijn.
5. RGI is nog niet tijdens een echte route bevestigd.
6. Dag/nacht wisselde in eerdere versies niet betrouwbaar.
7. Telnet en USB-CarPlay kunnen elkaar beïnvloeden.
8. Kaartmenu-items verbergen is niet veilig opgelost; lege BAP-capabilities kunnen de videolaag verstoren.
9. Notificaties vereisen actieve CarPlay en iOS/app-permissies.
10. Het actuele artifact is nog niet aan een commit/tag gekoppeld.

## 7. Afgewezen oplossingen

Niet opnieuw proberen zonder nieuw hard bewijs:

- zoominput twee- of driemaal herhalen;
- `setMapScale` volledig consumeren;
- de volledige Java-bridge direct permanent laden;
- moderne shellsyntax gebruiken die oude QNX-ksh niet accepteert;
- IPv4-only ontvangst;
- willekeurige luisterpoorten buiten de bewezen 7000–7001-route;
- decoder en EGL in hetzelfde proces;
- context overnemen vóór geldig IDR/bruikbaar beeld;
- 60/120 seconden als permanente runtime;
- aannemen dat een build automatisch in de ZIP zit;
- satelliet-providerlogo's behandelen als CarPlay-overlay.

## 8. Build- en teststatus

### QNX

```powershell
docker run --rm `
  -v "D:\Software Development\Github\porsche-carplay:/src" `
  -w /src qnx65-armv7:4.9 `
  sh build-tools/build_qnx.sh /src
```

Verwacht: `PORSCHE_QNX_BUILD_PASS ARM EABI5; ...`

### Linux-tests

```powershell
docker run --rm `
  -v "D:\Software Development\Github\porsche-carplay:/work" `
  -w /work python:3.13-bookworm `
  bash -lc "pip install -q pytest && pytest -q"
```

Laatste resultaat: `54 passed`. Windows-pytest gaf eerder valse fouten doordat fixtures `/bin/sh` verwachten.

### Package

```powershell
python build-tools/build_profile_sd_zip.py
Get-FileHash build\porsche-carplay-profiles-MU1417.zip -Algorithm SHA256
```

## 9. PuTTY/Telnet naar de unit

### Voorwaarden

**Bevestigd uit eerdere tests.** Het tijdens ontwikkeling gebruikte unitadres is `172.16.250.248`. Dit kan veranderen door de verbinding/netwerkconfiguratie. De laptop moet op dezelfde unitverbinding/subnet zitten. USB-CarPlay en Telnet waren niet altijd gelijktijdig stabiel; bij time-out eerst CarPlay/USB-status en netwerk controleren.

### PuTTY-instellingen

1. Open PuTTY.
2. `Host Name (or IP address)`: `172.16.250.248`.
3. `Connection type`: **Telnet**.
4. `Port`: **23**.
5. Open de verbinding.
6. Log in als `root`.
7. Publiek bekende standaard RCC-rootwachtwoord voor deze firmwarefamilie: `kuaRoJgY`.

Dit is een publiek firmware/default credential, geen persoonlijke gebruikerssecret. Gebruik het niet voor andere hosts en neem geen nieuwe/private credentials op in Git.

### QNX-shellbeperkingen

- Dit is een beperkte QNX-shell; commando's als `uname` en `sync` kunnen ontbreken.
- Plak geen prompttekst zoals `/ >` mee.
- Voer herstelcommando's bij voorkeur regel voor regel uit; een mislukte `set -e`-groep kan halverwege stoppen.
- Gebruik `/bin/ksh` wanneer een script expliciet via de MMX-kant moet draaien.
- Schrijf alleen naar `/mnt/app` nadat dit volume expliciet read-write is gemount en zet het daarna terug read-only.

### Veilige read-only controles

```sh
ls -l /mnt/app/eso/bin/apps/dio_manager
ls -l /mnt/app/eso/bin/apps/dio_manager.cw-stock
ls -l /mnt/app/eso/hmi/lsd/lsd.sh
ls -l /mnt/app/eso/hmi/lsd/lsd.sh.cw-stock
ls -l /mnt/app/eso/hmi/connectwow-carplay/controls-v15
ls -l /ramdisk/cw-link-probe-20261102
cat /mnt/persist/connectwow-carplay/session.status
tail -100 /mnt/persist/connectwow-carplay/renderer.log
tail -100 /mnt/persist/connectwow-carplay/capture.log
pidin ar
```

Niet ieder QNX-image heeft GNU-opties; houd commando's eenvoudig.

### Runtimepaden

- V15: `/mnt/app/eso/hmi/connectwow-carplay/controls-v15/`
- RAM: `/ramdisk/cw-link-probe-20261102/`
- persistent: `/mnt/persist/connectwow-carplay/`
- stock DIO: `/mnt/app/eso/bin/apps/dio_manager.cw-stock`
- stock HMI: `/mnt/app/eso/hmi/lsd/lsd.sh.cw-stock`

### Relevante events

- `CARPLAY_SOURCE_STABILIZING`
- `CARPLAY_SOURCE_STATE`
- `CARPLAY_DISPLAY_PREFLIGHT_FAILED`
- `CARPLAY_CONTEXT_NOT_AVAILABLE`
- `CARPLAY_WORKER_STARTED`
- `CARPLAY_ACTIVE`
- `CARPLAY_BLANK_RESTORED_OEM`

### Bestandsoverdracht

Gebruik bij voorkeur de SD/Online Menu-package. Voor kleine diagnostische staging kan `build-tools/telnet_push.py` worden gebruikt. Geef het wachtwoord als tijdelijke environmentvariabele en verwijder die daarna:

```powershell
$env:CW_TELNET_PASSWORD='kuaRoJgY'
python build-tools/telnet_push.py <lokaal-bestand> <remote-doel>
Remove-Item Env:CW_TELNET_PASSWORD
```

Lees de helper vóór gebruik; stage eerst naar RAM en verifieer hashes voordat iets onder `/mnt/app` wordt vervangen.

### Native payload uitsluitend vanuit RAM testen

**Bevestigd uit de repository.** `unit/carplay_ram_test.sh` is het bestaande niet-installerende native testpad. Het kopieert de gehashte payload vanaf SD naar `/ramdisk/connectwow-carplay-test`, start de originele `dio_manager.cw-stock` met de capture/RGI-preloads, start de supervisor en schrijft de resultaten terug naar SD. Het schrijft niets naar `/mnt/app`.

Bouw de bestaande RAM-testoverlay met:

```powershell
python build-tools/build_ram_test_zip.py
```

Pak `build/porsche-carplay-RAM-test-MU1417.zip` uit over de Online Menu-SD-kaart, werk het menu bij en kies `CarPlayRAM > Start CarPlay RAM-test (60 sec)`. Logs komen in `connectwow-carplay-logs/latest/` op de SD-kaart.

Handmatige equivalent op de unit, uitsluitend nadat de payload en `payload.manifest` op SD staan:

```sh
/bin/ksh /scripts/online/carplay_ram_test.sh
```

Het exacte scriptpad is afhankelijk van hoe Online Menu de SD-overlay mount/kopieert; gebruik daarom bij voorkeur de menuactie. Controleer vóór de test dat `/mnt/app/eso/bin/apps/dio_manager.cw-stock` bestaat en uitvoerbaar is.

Belangrijke beperking: deze bestaande RAM-test is begrensd op 60 seconden en zet `CW_RGI_ENABLE=0`. Hij is geschikt voor native video/cold-startdiagnostiek, niet voor een volledige duurzame V15- of fysieke RGI-test. Verander dit niet stilzwijgend; bouw voor een langere proef een expliciet nieuw testprofiel met eigen logging en stop/herstelactie.

### Los native artifact via Telnet naar RAM stagen

Voor een klein binair bestand of `.so` kan de helper rechtstreeks naar een RAM-pad sturen, bijvoorbeeld:

```powershell
$env:CW_TELNET_PASSWORD='kuaRoJgY'
python build-tools/telnet_push.py build\qnx\libcw-porsche-capture_receiver.so /ramdisk/cw-upload-receiver.so
Remove-Item Env:CW_TELNET_PASSWORD
```

De helper verstuurt hex naar `<doel>.hex`; hij decodeert of activeert het bestand niet. Laat een volgende sessie eerst de helper en de actuele unittools controleren en decodeer daarna alleen met de op deze QNX-unit beschikbare, eerder geteste methode. Verifieer altijd SHA-256 met de meegeleverde `cw-window-candidate --hash` vóór gebruik. Vervang geen live preloadlibrary in-place; stage naar een nieuwe naam en start een afzonderlijke proef.

### Java-JARs zijn niet hot-loadbaar vanuit RAM

**Bevestigd uit de launchers.** De HMI-JARs worden via `VMOPTIONS="$VMOPTIONS -Xbootclasspath/p:$JAR"` geladen voordat de OEM `lsd.sh` de Java-VM start. Een JAR naar `/ramdisk` kopiëren injecteert hem dus niet in een reeds draaiende JVM.

Voor een Java-test zijn twee verschillende stappen nodig:

1. De JAR kan eerst naar RAM of een tijdelijke profielmap worden gestaged en gehasht.
2. Een one-shot HMI-wrapper moet vóór JVM-start `-Xbootclasspath/p:<exact-pad>` instellen en daarna `lsd.sh.cw-stock` uitvoeren.

De bewezen veiligheidsvorm staat in `unit/lsd_controls_watchdog.sh` en `unit/lsd_notifications_watchdog.sh`: `pending` wordt vóór de proef verwijderd, `attempted` wordt gezet, en zonder latere expliciete `confirmed`-marker gebruikt de volgende boot stock-HMI. Voor de open split-JAR-tests moet dit patroon per JAR worden uitgebreid. Gebruik niet de gecombineerde bridge en probeer geen draaiende JVM te patchen.

Een Java one-shottest vereist een RCC/HMI-herstart en kan de navigatiestart blokkeren. Controleer daarom vóór iedere proef:

- geldige `lsd.sh.cw-stock` en hash;
- een automatische stock-fallback op de volgende boot;
- logoutput naar SD;
- een handmatig PuTTY-herstelpad wanneer HMI niet opkomt.

De exacte split-JAR one-shotinstallaties bestaan nog niet als afzonderlijke menuacties; dat is bewust een open vervolgstap, geen ontbrekend commando dat een volgende sessie moet raden.

### Mount en reboot

Alleen gebruiken als de geplande installatie/herstelactie dat vereist:

```sh
mount -uw /mnt/app
# gecontroleerde, gehashte en atomische bestandsactie
mount -ur /mnt/app
on -f rcc /usr/apps/mib2_ioc_flash reboot
```

Controleer vóór reboot dat stockback-ups bestaan en dat `/mnt/app` weer read-only is. Het rebootcommando werkte eerder; sommige menuvarianten die “reset” beloofden deden feitelijk niets.

### Herstelprincipe

Gebruik bij voorkeur `restore-oem` uit `unit/carplay_profiles.sh` via Online Menu. Handmatig herstel alleen als HMI/PCM niet start en uitsluitend met de geverifieerde `.cw-stock`-bestanden. De exacte recoveryreeks moet eerst tegen actuele paden en hashes worden gecontroleerd; kopieer geen oude chatcommando's blind.

## 10. Geprioriteerde vervolgstappen

### 1 — dirty tree veiligstellen

Review `git diff`, bouw Java/split-JARs/QNX/tests/package in die volgorde, inspecteer profielinhoud en maak daarna een traceerbare commit of testtag.

### 2 — alleen native V15 cold-start

Installeer Controls V15 met OEM-HMI. Laat de auto volledig slapen en start koud.

Acceptatie:

- één stabilisatiefase;
- geen twee throw-away workers;
- één `CARPLAY_ACTIVE display=1 context=70 size=800x480`;
- betrouwbare reconnect;
- OEM-kaart bij afwezig/ongeldig CarPlay-beeld.

Als dit faalt: vergelijk owner PID, geometry-epoch en `dmdt gs/gd`. Verhoog niet blind de 1,2 seconden.

### 3 — one-shot zoom-JAR

Maak een afzonderlijke Online Menu-proef voor `PorscheCarPlayZoom.experimental.jar` met automatische OEM-HMI-terugval.

Controleer navigatiestart, één stap per klik, richting, veranderende schaal, queue-omkering, autozoom→kaart terug en volledig OEM-gedrag zonder verse lease.

### 4 — one-shot guidance-JAR

Eerst gecontroleerde fixturestate, daarna echte Apple Maps-route. Controleer pijl, rotonde/afrit, afstand, heartbeat, straat, remaining distance/time, lanes en clear.

### 5 — nav-ignore/notificaties en displayhook

Test afzonderlijk. Display-JAR als laatste wegens hoger bootrisico.

### 6 — pas daarna combineren

Activeer de gecombineerde bridge alleen nadat ieder onderdeel cold-start, reconnect en herstel heeft doorstaan.

## 11. Open vragen

1. Lost de 1,2-seconde stabilisatie de cold-startbug fysiek op?
2. Zijn twee stabiele displaymanagerqueries daarnaast nodig?
3. Welke autozoomsetting hoort bij de gewenste bediening?
4. Verandert de Porsche-schaal fysiek nu stock `setMapScale` doorloopt?
5. Welke Java-hook blokkeerde eerder navigatiestart?
6. Hoe gedragen Apple Maps, Google Maps en Waze zich met zoom/`showUI`?
7. Is RGI volledig voor rotondes, afritten en lanes?
8. Is dag/nacht stabiel na cold boot en reconnect?

## 12. Niet met zekerheid overdraagbaar

- Niet alle ad-hoc unitlogs en RAM-artifacts zijn bewaard.
- De exacte lokale paden naar recovered OEM-JARs en de gebruikte JDK-invocation zijn niet betrouwbaar gedocumenteerd; bepaal die opnieuw voor `build-tools/build.py`.
- De actuele toestand van unit en SD-kaart is onbekend; bij de laatste controle was de unit niet bereikbaar en was geen SD-volume zichtbaar.
- De actuele ZIP is lokaal verifieerbaar, maar nog niet aan een commit gekoppeld of fysiek gevalideerd.

## Zoomproef via Telnet ? voorbereiding 4 november 2026

- De gebruiker wil de aangepaste losse zoom-JAR eerst testen en bevestigde dat de auto stilstaat en het scherm kan worden bekeken.
- Read-only unitcontrole: `lsd.sh` en `lsd.sh.cw-stock` hebben beide de verwachte hash `7ad5a6a08589591c48ca0d492e1793977eb2256ec32474b08306b4f9882fc091`.
- Er staat al een permanente `lsd/jars/ConnectWowZoom.experimental.jar` met SHA-256 `414b7f653e96ab347e61ba3b56e479202b40e49af8d9702bbc70cd87d4a3512e`. Stock `lsd.sh` voegt JARs uit deze map toe aan BOOTCLASSPATH. Deze oude JAR moet v??r een nieuwe hookproef behouden buiten de autoloadmap worden gezet; niet dubbel laden.
- Native V15 meldt RUNNING. Er waren geen `/fs/sda0` of `/fs/sdb0` volumes zichtbaar.
- Nieuw lokaal: `unit/lsd_zoom_oneshot.sh` en `tests/test_zoom_oneshot.py`. De wrapper gebruikt een persistent eenmalig ticket, controleert stock/JAR-hashes, weigert activering zolang de oude JAR aanwezig is en valt bij volgende boot terug naar stock. Gerichte Linux-test: **1 passed**. Nog niet ge?nstalleerd of fysiek getest.
- Beoogde huidige zoompayload: `build/PorscheCarPlayZoom.experimental.jar`, SHA-256 `8b0ac8b5d883d7835f026756ac1e60b2b4bc4bc7822f051829d89750964cf478`.
- Overdracht via QNX-ksh octal-print naar nieuwe RAM-bestanden werd afgebroken v??r voltooide hashcontrole. Mogelijk gedeeltelijke bestanden: `/ramdisk/cw-zoom-20261104.jar`, `/ramdisk/cw-zoom-fast-20261104.jar`, `/ramdisk/cw-zoom-final-20261104.jar`. Niet activeren of als geldige payload behandelen.
- Daarna weigerde Telnet een nieuwe consolesessie met `telnetd: login_tty: Operation not permitted`. Oorzaak niet vastgesteld. Er is geen HMI-starter/JAR op `/mnt/app` gewijzigd en geen herstart uitgevoerd.
- Volgende stap: Telnet-console herstellen/controleren en overdracht betrouwbaar afronden met doelhashcontrole. Pas daarna de transactionele one-shotinstallatie uitvoeren, de oude JAR bewaren en de zichtbare proef starten. Bestaande `unit/zoom_test.sh` is permanent en biedt geen one-shotterugval.

### Fysieke zoomproef 4 november 2026

- **Fysiek bevestigd:** de one-shot-JAR werd geladen, de HMI startte en de native lease op UDP 7032 bleef actief. De lease-ID verandert bij iedere heartbeat en is dus geen stabiele sessie-ID. Een Java-queue mag een gewijzigde lease-ID niet zelfstandig als rendererwissel behandelen.
- **Fysiek afgekeurd:** de variant die de volledige stock `CombiBAPListener.setMapScale(int)` liet doorlopen. De schaal begon op circa 1,5 km, maar na draaien veranderden autozoom en afstand naar `unavailable` respectievelijk `---`; CarPlay zoomde niet. Meerdere snelle stappen werkten alleen met de eerdere JAR.
- De gebruiker vindt de bewuste `unavailable`-weergave geschikt voor overige, werkelijk niet-ondersteunde kaartopties. Gebruik dit mechanisme niet voor autozoom.
- De unit is daarna teruggezet naar stock `lsd.sh` plus de eerder werkende `ConnectWowZoom.experimental.jar` (SHA-256 `414b7f653e96ab347e61ba3b56e479202b40e49af8d9702bbc70cd87d4a3512e`) en opnieuw gestart.
- Volgende implementatie: stuur zoom semantisch naar CarPlay, behoud een begrensde geldige Porsche-schaal/ACK en laat autozoom zijn stockstatus behouden. Test eerst één klik per richting, grenzen, autozoom en OEM-fallback.

### Zoom- en cold-startcorrecties na fysieke proef

- **Bevestigd uit unitlogs:** CarPlay werd pas rond 6,5 minuut na RCC-start actief. Vooraf gingen veel `CARPLAY_WORKER_STARTED`, `CARPLAY_DISPLAY_PREFLIGHT_FAILED` en `CARPLAY_RENDERER_FAILED stage=displayables-query` meldingen; daarna verscheen `CARPLAY_ACTIVE display=1 context=70 size=800x480` en werd de ready-lease iedere twee seconden vernieuwd.
- **Bevestigd uit bronvergelijking:** `harman-f/mhi2_altscreen_carplay` gebruikt voor zoom een begrensde signed backlog en 140 ms minimale afstand tussen semantische opdrachten. `omonob/MHI2-Carplay-Maps` en `chefranov/mhi2-au37x-carplay` houden één supervisor/renderer-eigenaar vast en vermijden ongecontroleerde parallelle overnamepogingen. Deze repos zijn alleen als ontwerpreferentie gebruikt; hun firmwarebinaries zijn niet overgenomen.
- `PorscheClusterControls` gebruikt nu één opdracht per detent, 140 ms pacing en een begrensde geldigheid van 1000 ms. MU1417-heartbeat-ID's worden niet langer als stabiele sessie-ID behandeld; verse CRC-lease en queuegrens bewaken fallback.
- De ASM-hook slaat bij actieve CarPlay alleen de native verborgen-map-zoomside-effect over, roept wel Porsche `updateMapScale()` aan en behoudt daarmee de laatst geldige schaal/ACK. `setMapScaleSetting()` loopt volledig stock door; autozoom mag niet `unavailable` worden.
- De YUV-renderer hergebruikt de onmiddellijk voorafgaande, geserialiseerde supervisor-preflight. De dubbele `gd`-query in het kind is verwijderd; die race veroorzaakte cold-start-workerchurn. Mislukte supervisorpreflight wordt na 250 ms opnieuw gecontroleerd zonder worker te starten.
- Builds/tests: Java/fixtures slagen, QNX ARM EABI5-build slaagt, volledige suite **55 passed**, aanvullende regressies **4 passed**. Nieuwe zoom-JAR SHA-256: `d5af3d312b94336d49a597182f61b71c15c295ba26e96e3590e2cf7781aad3e1`; nieuwe native kandidaat: `6a93597f62278535a4b5d8906bdaca1db46d86eeec3813461f27124a68595294`.
- Nieuwe profiel-ZIP: `build/porsche-carplay-profiles-MU1417.zip`, SHA-256 `69f9c5b070291da37ec4fb2e9183f69e4e555d968fda5a7979690c04c3f5efcb`. Stable V14 in dit pakket blijft hash `950107cb...51072`; alleen Controls bevat de nieuwe native kandidaat.
- Deployment is **niet uitgevoerd**: vlak voor FTP-overdracht verdween `172.16.250.248` volledig van het netwerk (geen ping/Telnet). Er is in die poging niets naar de unit geschreven. Eerst bereikbaarheid herstellen, live hashes opnieuw lezen, dan transactioneel met aparte backups laden en fysiek testen.

### Referentie-audit zoom — 4 november 2026 (vervangt de timingconclusie hierboven)

- **Bevestigd uit primaire referentiecode:** de eerder overgenomen `140 ms` komt uit de experimentele, ACK-gestuurde `alt111_zoom`-state-machine van `harman-f/mhi2_altscreen_carplay`. Die implementatie houdt een stabiele sessie, focus/eigenaar en een expliciete `in_flight`/`complete(accepted)`-cyclus bij. Onze tekstuele UDP-keten op poort 7032 heeft geen ACK-retourpad. Alleen de 140 ms-constante overnemen was daarom geen geldige port.
- **Bevestigd uit de gepubliceerde MHI2-bediening van `omonob/MHI2-Carplay-Maps`:** `Mhi2ClusterControlBridge` gebruikt een begrensde FIFO van 16 en een enkele daemonworker. Een encoderdetent wordt onmiddellijk als precies één `zoom-in` of `zoom-out` UDP-commando afgevoerd, zonder debounce, 140/250 ms-pacing of verouderingstimer.
- `PorscheClusterControls` volgt nu die transportstructuur: FIFO 16, één opdracht per Porsche `MapScale`-stap, behoud van volgorde bij snelle omkering, verse native ready-lease vóór acceptatie én vóór verzending, en leegmaken bij verlies van de lease.
- De onbewezen vertaling van Porsche autozoom naar CarPlay `show-map` is verwijderd. `consumeMapScaleSetting()` retourneert `false`; de ASM-hook laat de volledige OEM-methode altijd doorlopen. Er is in de onderzochte referentiecode geen bewezen universeel CarPlay-autozoomcommando.
- De Porsche-specifieke `setMapScale`-hook blijft beperkt tot de fysiek gemotiveerde afwijking: tijdens actieve CarPlay wordt alleen de verborgen OEM-kaartincrement overgeslagen, waarna `updateMapScale()` de bestaande Porsche-status/ACK bijwerkt. Buiten CarPlay loopt de stockmethode volledig.
- Lokale verificatie na deze audit: volledige Linux-suite **58 passed**, OEM-Java-build en alle fixtures geslaagd, split-JARs geslaagd, QNX ARM EABI5-build geslaagd.
- Actuele zoom-JAR SHA-256: `264f4231e69c1ab24cf036b7e9a518d25374a3a5723b82b31647371c86779a82`.
- Actuele native kandidaat blijft SHA-256 `6a93597f62278535a4b5d8906bdaca1db46d86eeec3813461f27124a68595294`.
- Actuele profiel-ZIP SHA-256: `2fe9b08722c4ccd05925a7ede12460ddacf933fa1ff42678546ac45d5df307d4`.
- Afzonderlijke transactionele one-shot zoomproef: `build/porsche-carplay-zoom-test-MU1417.zip`, SHA-256 `37a51aef493eb127f940d719ec08690c4cec12f7b16afb80d2dddc8e002caa51`.
- **Nog niet fysiek bevestigd en niet gedeployed:** één detent, snelle serie, omkering, zichtbare schaalfeedback en OEM-autozoom. De nieuwste bestanden mogen pas als werkend worden bestempeld nadat deze afzonderlijk via de one-shotproef zijn bevestigd.

### Gecombineerde Java-one-shot — 6 november 2026

- De gebruiker wil displayrouting, zoom, routegeleiding en notificatiecompatibiliteit als één proef testen. Er wordt geen zelfstandige nav-ignoreproef meer gebouwd.
- `PorscheCarPlayBridge.experimental.jar` bevat deze combinatie. De notificatiecompatibiliteit gebruikt technisch de bestaande `AppState`-patch: alleen `getAppStateID()` en `getOwner()` worden geneutraliseerd; `getSpeechMode()` en de OEM-popup-/speechroute blijven intact. Dit is onderdeel van notificaties, geen afzonderlijk gebruikersfeature.
- `install-controls` blijft bewust native V15 met stock-HMI installeren. De nieuwe actie `test-controls-java` vereist eerst een geldige Controls-installatie, maakt een eenmalig `pending`-ticket, activeert transactioneel `lsd-controls.sh` en herstart de RCC.
- Zonder expliciete bevestiging wordt de JAR na die ene poging niet opnieuw geladen. `confirm-controls` weigert nu bevestiging zolang geen `attempted`-marker bestaat.
- Het Online Menu bevat afzonderlijk: native Controls installeren, gecombineerde Java-bridge eenmaal testen, en pas daarna bevestigen.
- `split_hmi_bridge.py` bouwt geen zelfstandig `PorscheCarPlayNavIgnore.experimental.jar` meer. Display, zoom en guidance blijven beschikbaar voor diagnose; de afzonderlijke notificatie-JAR blijft voor V14.6 bestaan.
- Verificatie: OEM-Java-build en alle fixtures geslaagd, QNX ARM EABI5-build geslaagd, volledige Linux-suite **59 passed**. De uiteindelijke profiel-ZIP bevat alle zeven vereiste OEM/helperklassen, de nieuwe menuactie en de one-shotwrapper.
- Actuele profiel-ZIP: `build/porsche-carplay-profiles-MU1417.zip`, SHA-256 `ebb7862f105ca44e8e905bacba6ab93b5767855c96a9b52139b620fcdd87545c`.
- Gecombineerde bridge in dat pakket: SHA-256 `bfffaa8e9a869168cbf9c398dcc42ba8d6c6030b4e3fb048db4d87661a9f522f`.
- **Niet fysiek bevestigd en niet gedeployed.** Eerst native V15 normaal laten starten; daarna pas de gecombineerde one-shot uitvoeren en boot, navigatie, display, zoom, routegegevens, notificaties en volgende-bootfallback controleren.
