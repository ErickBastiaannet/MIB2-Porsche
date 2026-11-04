# Projectinstructies voor Codex

## Context opbouwen

1. Werk vanuit de repositoryroot `D:\Software Development\Github\porsche-carplay`.
2. Lees vóór bestaand werk voort te zetten:
   - `docs/CODEX_HANDOVER.md` voor de actuele status, dirty tree en eerstvolgende stappen;
   - `README.txt` voor ondersteunde functionaliteit en gebruik;
   - `PHYSICAL-BASELINE.md`, `firmware-profile.json` en `verified-window-profile.json` voor fysiek bewijs en exacte firmware-/displaygegevens.
3. Controleer altijd `git status --short` en `git diff`. De werkboom kan geldige, nog niet gecommitte wijzigingen van de gebruiker bevatten. Reset, overschrijf of verwijder die niet.
4. Behandel claims als één van: fysiek bevestigd, lokaal getest, afgeleid uit firmware/referentiecode, of nog onbevestigd. Presenteer die categorieën niet als gelijkwaardig.

## Projectdoel en bereik

Dit project toont de alternatieve CarPlay-videostroom op het rechter instrumentenscherm van een Porsche Panamera met firmware `MHI2_ER_POG24_K5137_MU1417_971919360T`. Het voegt daarnaast bediening via bestaande Porsche-functies, iAP2 Route Guidance naar het cluster, CarPlay-notificatiecompatibiliteit en veilige SD/Online Menu-installatie en herstel toe.

Ondersteun geen andere firmware zonder afzonderlijke analyse, exacte OEM-hashes, builds en fysieke validatie. Dit is niet de ConnectWow-webbackend; verkeer, satelliettegels en providerproxying vallen buiten deze repository.

## Architectuur en technologie

- Native C99/QNX 6.5 ARM EABI5 verzorgt AirPlay/CarPlay-capture, H.264/AVCC-decode, I420/KD/EGL-rendering, displaymanagercontext, framekwaliteitscontrole, sessiebeheer en RGI-publicatie.
- Java met legacy/CDC-compatibele bytecode haakt exact geverifieerde OEM-klassen voor context, zoom en Porsche-BAP-routegeleiding.
- Python bouwt, splitst, verpakt en valideert artifacts.
- Oude QNX `ksh`-scripts verzorgen launchers, transactionele profielinstallatie, rollback, logging en OEM-herstel.
- Docker levert Linux-tests en de crosscompilerimage `qnx65-armv7:4.9`.
- Online Menu op SD is het reproduceerbare installatie- en herstelpad.

Runtimeafhankelijkheden:

1. Native capture publiceert korte CRC-beveiligde leases/states in `/ramdisk`.
2. `cw-window-candidate` superviseert decoder, renderer, displaymanager en OEM-terugval.
3. Java leest de native ready/context/guidance-state en stuurt bestaande OEM-methodes aan.
4. Native controls ontvangen Java-commando's via UDP-loopbackpoort 7032.

## Belangrijkste modules

- `native/porsche_unit.c`: supervisor, decoder-child, rendereractivatie en OEM-terugval.
- `native/porsche_session.*`: sessiestatemachine.
- `native/porsche_dm.*`: displaymanagerquery en contextwissel.
- `native/porsche_window*`, `porsche_yuv*`, `porsche_parser*`, `porsche_pixels*`: videopipeline.
- `native/porsche_frame_quality.*`: blokkeert zwart, leeg of onbruikbaar beeld.
- `native/porsche_geometry*`, `porsche_wire.*`: atomische runtimeprotocollen.
- `native/porsche_rgi.*`: iAP2 Route Guidance parser/mapping/publicatie.
- `java/org/connectwow/carplay/PorscheCluster.java`: context en verse CarPlay-lease.
- `java/org/connectwow/carplay/PorscheClusterControls.java`: zoom- en kaartbediening.
- `java/de/audi/tghu/navi/app/cluster/PorscheRouteGuidance.java`: guidance-state naar bestaande Porsche-BAP-methodes.
- `build-tools/BuildPorscheHooks.java`: ASM-hooks in exact geverifieerde OEM-klassen.
- `build-tools/build.py`: Java-build en fixtures.
- `build-tools/split_hmi_bridge.py`: onafhankelijke display-, zoom-, guidance- en nav-ignore-JARs.
- `build-tools/prepare_native.py`, `build_qnx.sh`: firmwaregebonden native generatie en crossbuild.
- `unit/carplay_profiles.sh`: gehashte transactionele installatie, rollback en herstel.
- `unit/dio_manager_controls.sh`: Controls-runtime.
- `unit/lsd_controls_watchdog.sh`: one-shot/confirmed Java-wrapper.
- `build-tools/build_profile_sd_zip.py`: gecombineerd SD/Online Menu-pakket.
- `verified/v14/`: fysiek bewezen native herstelbasis; behandel als immutable baseline.

## Blijvende ontwerpregels

1. **Behoud Stable V14.** Vervang `verified/v14/` niet zonder expliciete nieuwe fysieke bewijsronde. Nieuwe functies horen in een afzonderlijk profiel.
2. **Fail safe naar OEM.** Neem context pas over na bruikbaar beeld; herstel OEM onmiddellijk bij zwart/ongeldig/stilgevallen beeld of sessieverlies.
3. **Scheid decoder en EGL-renderer.** Combineer deze niet opnieuw in één proces.
4. **Gebruik IPv6 en de bewezen CarPlay-route op TCP 7001.** Introduceer geen willekeurige listenerpoort.
5. **Behoud OEM-semantiek.** Laat originele Porsche-state, ACKs en schaaladministratie doorlopen tenzij fysiek bewezen is dat consumptie veilig is.
6. **Eén zoomopdracht per OEM-stap.** Vermenigvuldig zoominput niet kunstmatig. Queue nooit input over een sessie/renderer-epoch heen.
7. **Verzin geen CarPlay-API.** Gebruik alleen in firmware, protocolcaptures of betrouwbare referentiecode aangetoonde functies. `showUI` is een kaart-terughaalactie, geen bewezen universele zoomreset.
8. **Test Java-hooks geïsoleerd.** Activeer de gecombineerde bridge pas nadat split-JARs één voor één one-shot en fysiek zijn bevestigd.
9. **Alle installaties zijn transactioneel.** Verifieer bron en doel met hashes, bewaar geverifieerde stockbestanden, wissel atomair, remount read-only en houd een werkend OEM-herstelpad.
10. **Gebruik QNX-compatibele shell.** Vermijd moderne shellsyntax die de oude `ksh` niet accepteert. Laat packaging- en syntaxtests slagen.
11. **Beperk logging en resources.** Geen ruwe telefoonvideo persistent opslaan. Roteer/begrens logs en schrijf diagnostiek naar SD wanneer beschikbaar.
12. **Geen private geheimen in Git.** Neem geen persoonlijke wachtwoorden, tokens, sleutels of private certificaten op. Het publiek bekende standaard RCC-rootcredential voor deze firmware mag uitsluitend als herkenbare factory/default referentie in de handover staan; nieuwe of gewijzigde credentials nooit vastleggen.

## Codeconventies

- C: C99, bestaande `cw_`-prefix en kleine, expliciete statefuncties; compileer met `-Wall -Wextra -Werror`.
- Java: blijf binnen de APIs van de doel-JVM; geen `StringBuilder`, `java.nio`, lambdas, invokedynamic of moderne runtimeafhankelijkheden. Vang boundary-fouten af zodat OEM-HMI blijft functioneren.
- Runtimebestanden: gebruik versie/magic, bounds, timestamp/freshness en CRC; schrijf atomair via tijdelijk bestand plus rename.
- Shell: fail closed, quote paden/variabelen, controleer elke kopie/hash/mount, en garandeer rollback/remount bij fouten.
- Python/build: deterministische archives en manifesten; stop op onbekende firmwareklassen, hashes of onopgeloste placeholders.
- Tests: voeg een fixture/regressietest toe voor iedere protocol-, mapping-, lifecycle- of packagingwijziging.
- Naamgeving: behoud bestaande `PorscheCarPlay*`, `cw-*`, profielnamen `v14`, `v14-5`, `v14-6`, `controls-v15` en runtimeprotocolnamen.

## Werkwijze bij wijzigingen

1. Bepaal eerst of de wijziging native, Java, launcher of packaging betreft; controleer vervolgens de volledige keten tot het daadwerkelijk geïnstalleerde artifact.
2. Wijzig de kleinste laag die het probleem veroorzaakt. Voeg geen timeout/multiplier toe zonder logbewijs.
3. Controleer na Javawijzigingen hookaantallen, bytecodeverificatie, split-JARinhoud en legacy classversie.
4. Controleer na native wijzigingen zowel QNX-build als hosttests.
5. Controleer na packagingwijzigingen welk binair bestand elk profiel werkelijk bevat; een geslaagde build bewijst niet dat de ZIP dat artifact gebruikt.
6. Installeer experimentele HMI-code als one-shot met automatische stock-terugval. Bevestig pas na succesvolle navigatiestart en functieproef.
7. Werk `docs/CODEX_HANDOVER.md` bij wanneer actuele status, hashes, blockers of volgende stappen veranderen. Zet blijvende projectregels alleen hier in `AGENTS.md`.

## Build en test

Voer uit vanuit de repositoryroot.

QNX-build:

```powershell
docker run --rm `
  -v "D:\Software Development\Github\porsche-carplay:/src" `
  -w /src qnx65-armv7:4.9 `
  sh build-tools/build_qnx.sh /src
```

Volledige tests onder Linux:

```powershell
docker run --rm `
  -v "D:\Software Development\Github\porsche-carplay:/work" `
  -w /work python:3.13-bookworm `
  bash -lc "pip install -q pytest && pytest -q"
```

Gebruik Windows-pytest niet als bewijs voor shellfixtures; die verwachten `/bin/sh`.

Java-build vereist recovered OEM-JARs en een geschikte JDK:

```powershell
python build-tools/build.py --oem-jar <recovered-oem.jar> --display-jar <recovered-display.jar> --jdk <jdk-directory>
python build-tools/split_hmi_bridge.py
```

SD-pakket:

```powershell
python build-tools/build_profile_sd_zip.py
Get-FileHash build\porsche-carplay-profiles-MU1417.zip -Algorithm SHA256
```

Minimale eindcontrole:

```powershell
git diff --check
git status --short
```

## Debug en fysieke tests

- Unit-runtime: `/ramdisk/cw-link-probe-20261102/`.
- Persistente logs: `/mnt/persist/connectwow-carplay/`.
- SD-logs: `connectwow-carplay-logs/` op `/fs/sda0` of `/fs/sdb0`.
- Relevante events staan in `docs/CODEX_HANDOVER.md`.
- Gebruik `build-tools/telnet_push.py` met credentials via een tijdelijke environmentvariabele en ruim die variabele na gebruik op. Zie de handover voor de bekende factory/default testtoegang.
- Start zichtbare tests uitsluitend wanneer de auto stilstaat.
- Vraag de gebruiker vlak vóór een zichtbare test of die naar het juiste scherm kijkt; start daarna direct en meld het resultaat zonder lange stilte.
- Telnet en USB-CarPlay kunnen elkaar beïnvloeden. Trek geen conclusies uit één mislukte connectie zonder sessie-/proceslogs.
- Gebruik voor een volledig native RAM-only veldtest de bestaande `build-tools/build_ram_test_zip.py` en `unit/carplay_ram_test.sh`; deze schrijft niet naar `/mnt/app`, duurt 60 seconden en heeft RGI uitgeschakeld.
- Behandel Java anders dan native code: een JAR kan niet in een al draaiende HMI-JVM worden hot-loaded. Gebruik een one-shot wrapper met `-Xbootclasspath/p:` vóór `lsd.sh.cw-stock`, automatische stock-fallback en RCC/HMI-herstart. Zie de handover voor de exacte huidige mogelijkheden en beperkingen.

## Deployment en herstel

- Gebruik bij voorkeur het gehashte SD/Online Menu-profielpakket.
- Houd een afzonderlijke Stable V14- en OEM-herstelactie beschikbaar.
- Controleer firmware en stockhashes vóór schrijven.
- Verander nooit tegelijk DIO en HMI zonder geborgde rollback.
- Voor wijzigingen aan starters/Java-hooks is een volledige RCC-herstart vereist; het bekende commando is `on -f rcc /usr/apps/mib2_ioc_flash reboot`, maar controleer altijd dat het werkelijk is uitgevoerd.
- Claim een functie pas als fysiek bevestigd wanneer schermobservatie en relevante logs beide kloppen.

## Bekende valkuilen en gebruikersafspraken

- Eerdere gecombineerde Java-injectie blokkeerde navigatiestart; niet opnieuw rechtstreeks permanent activeren.
- Eerdere zoommultipliers, volledige `setMapScale`-consumptie, IPv4-only ontvangst, willekeurige poorten en decoder+EGL in één proces zijn afgewezen.
- De gebruiker wil concrete voortgang en resultaat. Geef tijdens lang werk korte updates en vermijd herhaald speculatief testen.
- De gebruiker wil SD-updates én terugkeer naar de stabiele basis, met logs op SD.
- Koppel nieuwe bediening alleen aan bestaande, aangetoonde OEM/CarPlay-functies.
- Lees voor de actuele bugs, dirty tree en prioriteiten altijd `docs/CODEX_HANDOVER.md`.
