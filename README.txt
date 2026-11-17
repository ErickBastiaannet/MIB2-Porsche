ConnectWow CarPlay cluster voor Porsche PCM4 / MHI2
=================================================

Status bijgewerkt: 16 november 2026

Doel en ondersteunde firmware
----------------------------
CarPlay-kaartbeeld op het rechter instrumentenscherm van de Porsche Panamera,
met zoom via de bestaande Porsche-bediening en native routeaanwijzingen op
het guidancescherm van de teller.

Uitsluitend onderzocht en gebouwd voor:

  MHI2_ER_POG24_K5137_MU1417_971919360T

Display: 800 x 480, displaymanager-index 1 / backend 4, context 70,
CarPlay-videolaag 78. Dit zijn de gegevens van de onderzochte Panamera;
geen ondersteuning voor andere firmware of tellers uit afleiden.

Dit project is de CarPlay-integratie. ConnectWow-webdiensten, traffic,
satellietbeeldproviders en hun licenties behoren tot de aparte backend.

Huidige status op de Panamera
----------------------------
Fysiek bevestigd:

* Apple Maps- en Google Maps-kaartbeeld rechts naast de toerenteller.
* Kaart en routeaanwijzingen tegelijk zichtbaar met de huidige guidanceversie.
* Zoom werkte in eerdere fysieke proeven; de Porsche-meterschaal is geen
  betrouwbare afspiegeling van de zoomschaal van iedere CarPlay-app.
* Terugkeer naar de originele kaart na einde van eerdere kaartproeven.
* De nieuwe video-starter start de originele CarPlay-ontvanger met de benodigde
  capture-omgeving. Na de afgesproken herstart waren kaart en guidance zichtbaar.
* Het oude Google-logo is tijdens CarPlay niet zichtbaar, ook met de originele
  satellietweergave ingeschakeld.

De gebruiker heeft de guidanceversie, video-starter en logo-optie permanent
laten activeren. Permanent betekent dat ze bij volgende starts geselecteerd
blijven; het is geen bewijs van een afgeronde koude-start- of duurtest.

Nog niet volledig fysiek bevestigd:

* Meerdere slaap-/koude starts, USB-reconnects en langere ritten zonder uitval.
* Alle manoeuvretypen, pijlmomenten, rotondes, rijstroken en appwisselingen.
* Bestemmingsadres, ETA, route stoppen en aankomst in alle schermsituaties.
* Originele satellietlogo-weergave na CarPlay-terugval. De melding is in de
  runtime-log wel teruggekeerd, maar het herstelde beeld is niet apart bevestigd.
* Meldingen van alle gewenste iPhone-apps buiten de zichtbare CarPlay-interface.

De actuele live hashes, back-ups en resterende controles staan in
  docs/CODEX_HANDOVER.md
Historische fysieke basis:
  PHYSICAL-BASELINE.md
  firmware-profile.json
  verified-window-profile.json

Werking
-------
Kaart en opstarten
* De native capture ontvangt de alternatieve CarPlay-videostroom. Decoder en
  renderer zijn gescheiden processen. Zwart, ongeldig of ontbrekend beeld mag
  de originele Porsche-kaart niet vervangen; een verse rendererlease bepaalt
  wanneer de CarPlay-uitvoer beschikbaar is.
* unit/carplay_receiver_start.sh zet de video-omgeving expliciet en wordt via
  exec de originele dio_manager.cw-stock, met behoud van PID/watchdogeigendom.
  Dit verhelpt de waargenomen start zonder capturebibliotheek. Herhaald starten
  en reconnecten blijven onderdeel van de duurtest.
* Alleen apps die een geschikte alternatieve CarPlay-stroom leveren kunnen
  kaartbeeld tonen. Apple Maps en Google Maps zijn fysiek gezien; volledige
  apppariteit, waaronder Waze, is niet bewezen.

Zoom en kaartmenu
* De bestaande Porsche MapScale-bediening wordt naar semantische CarPlay-
  zoomcommando's vertaald. De huidige Java-keten gebruikt een begrensde FIFO,
  zonder de eerder uitgeprobeerde kunstmatige debounce-/pacingvertraging.
  Zoominput wordt niet vermenigvuldigd en mag geen oude sessie overleven.
* De CarPlay-app bepaalt de werkelijke zoom en schaal. Een vast of afwijkend
  meterlabel in het Porsche-menu bewijst niet dat de app op die schaal staat.
* Een universele CarPlay-autozoom of zoomreset is niet aangetoond. De huidige
  consumeMapScaleSetting laat de OEM-instelling door; deze README belooft
  daarvoor geen CarPlay-reset of hercentreeractie.
* De originele kaartmenu's blijven bestaan. De teller opent die lokaal;
  lege BAP-capabilityvelden verborgen ze niet betrouwbaar en konden juist
  de videolaag verbergen. Die eerdere aanpak niet opnieuw blind toepassen.

Routeaanwijzingen
* Native iAP2 Route Guidance wordt verwerkt en via de bestaande Porsche-
  CombiBAPListener/BAP-weergave aangeboden. Geen zelf getekende manoeuvrepijlen.
* De verwerking omvat actuele manoeuvreselectie, deltas/prefetch, afstanden,
  rotondehoeken en zijtakken, rijstrookgegevens, volgende-weg-/afrittekst,
  bestemmingsadres, resterende routeafstand en ETA, stoppen en aankomst.
* Deze onderdelen zijn lokaal tegen fixtures en referenties gecontroleerd.
  Basisweergave is fysiek bevestigd; dat bewijst niet ieder detail hierboven.
* De bewezen ontvangst-/kaartketen is bij inhoudelijke guidancecorrecties
  beschermd tegen onbedoelde wijzigingen. Zie:
    docs/GUIDANCE_CHECKLIST_PROGRESS.md
    docs/GUIDANCE_REFERENCE_AUDIT.md
    docs/GUIDANCE_PORT_MATRIX.md

Google-logo uitsluitend tijdens CarPlay onderdrukken
* De originele satellietinstelling blijft behouden. Tijdens een geldige
  CarPlay-rendererlease wordt alleen de uitgaande BAP-kaartmodus gefilterd:
  Google Earth (1) wordt standaard (0). De opgeslagen OEM-kaartmodus en
  aanvullende kaartvelden blijven behouden.
* Bij leaseverlies wordt de laatste OEM-melding weer aangeboden. De log toont
  onderdrukken, herstellen en opnieuw onderdrukken. De afwezigheid van het
  logo tijdens CarPlay is fysiek bevestigd.
* Dit verwijdert geen satelliettegels of leveranciersvermelding en vervangt
  het tellerlogo niet door ConnectWow.
* De optie is afzonderlijk gebouwd in optional/satellite-logo/ en geactiveerd
  met connectwow.carplay.satelliteLogo=hide-during-carplay.
* BAP-functie 44 bevat kaartmodus/status, geen logo-afbeelding of downloadadres.
  Het precieze Google-bitmapbestand in de teller is niet aangetoond.
  Onderzoek: docs/SATELLITE_CLUSTER_LOGO.md

Appmeldingen
* Er is een afzonderlijke AppState-compatibiliteitsproef, gebaseerd op de
  navignore-semantiek: navigatie-eigendom wordt geneutraliseerd; speechmode
  en het originele CarPlay-popupkanaal blijven behouden.
* Dit is geen garantie dat iedere melding verschijnt. Een actieve CarPlay-
  verbinding en toestemming op de iPhone zijn nodig. iOS en de betreffende
  app bepalen welke inhoud wordt geleverd. Flitsmeister is niet gelijk aan
  gegarandeerde WhatsApp-/Telegram-achtige visuele meldingen.

Broncode en bouwen
-----------------
Belangrijkste onderdelen:

  native/                         QNX capture, decode, rendering, sessies, RGI
  java/                           Porsche-display-, zoom- en guidancekoppeling
  optional/satellite-logo/        Afzonderlijke logo-optie en gebruiksinstructies
  unit/                           QNX-starters, profielinstallatie en herstel
  build-tools/                    Builders, bytecodechecks en verpakkingen
  tests/                          Native, Java, shell- en protocolfixtures
  verified/v14/                   Ongewijzigde fysiek bevestigde herstelbasis

Lees AGENTS.md en docs/CODEX_HANDOVER.md voordat bestaand werk wordt voortgezet.
OEM-JARs, firmware en toolchains zijn lokale buildinputs; niet uit Git afleiden
of downloaden zonder de bestaande firmware-/hashcontrole te behouden.

Java (gebruik de bestaande, teruggewonnen OEM-buildinputs):

  python build-tools/recover_destination_api.py --recovery-root <recoverymap>
  python build-tools/build.py --oem-jar <oem.jar> --display-jar <display.jar> --jdk <jdk-bin>
  python build-tools/split_hmi_bridge.py

Native QNX-build, vanuit deze repository in PowerShell:

  docker run --rm -v "${PWD}:/src" -w /src qnx65-armv7:4.9 sh build-tools/build_qnx.sh /src

Native regressietests:

  docker run --rm --entrypoint /bin/sh -v "${PWD}:/src" -w /src qnx65-armv7:4.9 -c 'PATH=/usr/bin:/bin sh tests/run_native.sh /src'

Logo-lifecycle en beschermde guidancegrens (JDK beschikbaar via JAVA_HOME/PATH):

  python -m pytest tests/test_satellite_logo_probe.py tests/test_guidance_processing_boundary.py -q

Voor de logo-builder en bevestigde starter: optional/satellite-logo/README.md.
Een geslaagde build of fixture is geen bewijs van acceptatie door de fysieke
J9-VM, het tellerscherm of een complete rijtest.

SD-pakketten en actuele live reparaties
--------------------------------------
De bestaande profielbuilder:

  python build-tools/build_profile_sd_zip.py

maakt build/porsche-carplay-profiles-MU1417.zip met afzonderlijke V14-, V14.5-,
V14.6- en Controls V15-profielen en installatie-/herstelmogelijkheden via het
bestaande Online Menu. De oudere native kandidaat-ZIP is geen aanduiding van
de nieuwste live configuratie.

LET OP: de nieuwste losse video-bootstrap- en logo-reparaties zijn nog niet
volledig in de algemene SD-profielbuilder opgenomen. Een opnieuw gebouwde
profiel-ZIP is dus niet automatisch gelijk aan wat nu op de Panamera draait.
Voer geen oudere SD-installatie over de huidige werkende configuratie uit
zonder eerst de inhoud en hashes te vergelijken met CODEX_HANDOVER.md.

Gerichte builders/scripts voor recente wijzigingen:

  build-tools/build_guidance_patch.py --profile checklist
  build-tools/build_map_output_patch.py
  build-tools/prepare_receiver_start_config.py
  unit/install_receiver_bootstrap.sh
  build-tools/build_satellite_logo_probe.py
  build-tools/prepare_satellite_logo_launcher.py
  unit/confirm_satellite_logo.sh

Dit zijn firmware-/baselinegebonden hulpmiddelen, geen uitwisselbare universele
installers. Volg hun vereiste inputs, hashes, volgorde en bestaande back-ups.

Installatie, herstel en logging
------------------------------
* Installaties verifiëren bron/doel, bewaren de bekende originele bestanden,
  wisselen atomair waar ondersteund en remounten het appvolume read-only.
* Nieuwe Java-functies eerst afzonderlijk als eenmalige proef. Pas bevestigen
  nadat de navigatie start en de bedoelde functie fysiek is gezien.
* Geen zichtbare proef of PCM-herstart voordat de gebruiker stilstaat en vlak
  vooraf heeft bevestigd klaar te zitten.
* Het Online Menu bevat herstel van de originele HMI- en DIO-starters.
  De historische naam Restore original DIO kan beide herstellen. Een oudere
  hersteltool kan een nieuwere installatie terecht weigeren door hashverschil;
  gebruik dan het herstelpad dat bij die specifieke wijziging is vastgelegd.
* Exacte live back-ups, herstelcommando's, PuTTY/Telnet en RAM-overdracht staan
  in docs/CODEX_HANDOVER.md. Gebruik geen willekeurige QNX-/Linux-commando's:
  de oude shell en aanwezige utilities wijken af van een moderne Linux-host.
* Tijdelijke diagnostiek staat in /ramdisk. De logo-overgangen staan in
  /ramdisk/cw-satellite-logo.log (begrensd tot 64 regels per JVM-start).
  SD-logbeschikbaarheid verschilt per starter/profiel; niet alle diagnostiek
  wordt automatisch persistent opgeslagen.
* Geen privéwachtwoorden, tokens, telefoonvideo of firmwaredumps in Git.
  Deze integratie wijzigt geen hosts, certificaten, traffic- of licentiegegevens.


Porsche-routevoorrang (MU1417, fysiek getest 17-11-2026)
Een originele Porsche-route krijgt voorrang op de teller voor kaart en guidance.
Na stoppen van de Porsche-route keert geldig CarPlay-kaartbeeld automatisch terug.
De CarPlay-kaart blijft zonder actieve telefoonroute bruikbaar. De iPhone-route
wordt niet automatisch gestopt. Permanente activatie is op de testunit bevestigd;
zie docs/NAVIGATION_PRIORITY.md voor installatie, hashcontrole en herstel.
