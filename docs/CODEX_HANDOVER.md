# Actuele Codex-overdracht — Porsche CarPlay-cluster

## OFFLINE CONTROLE AFGEROND - routevoorrang, 17 november 2026

Gebruiker vroeg controle ZONDER auto. Geen verdere verbinding, installatie of
herstart geprobeerd. Nieuwe build-tools/verify_priority_rom_links.py controleert
constantpoolleden/signaturen en private toegang van kandidaatklassen tegen exacte
J9-ROM-metadata (rom.classes uit de bestaande MU1417-recovery). Gebruikt bestaande
ReaderStream/J9ROMMethod/J9ROMField, geen OEM-initializers of QNX-emulatie.

Deze controle vond een echte externe afhankelijkheid: ClusterService.showKombiMap
riep onbeschermd PorscheGeometry.setVisible(Z)V aan terwijl die klasse in noch
het splitpakket noch OEM-ROM zat. Dezelfde oude observer-hook zat al in de
gehashte baseline-guidance-JAR. Niet simpelweg de oude geometry publisher/JAR
bijvoegen: die kan een extra publisher/worker activeren naast native geometry.
BuildNavigationPriority.java verwijdert nu exact de bekende ILOAD1+invokestatic
observerstaart uit showKombiMap, met telling==1 en baseline-hashguards. Originele
MapInterface.showKombiMap-call blijft staan. Baseline-JARs en live unit niet gewijzigd.

Nieuwste kandidaat-JAR SHA
fedd4e15c80b9ae64f541c681502fdef18495e212c8e5097f657d153f6506995.
Audit:22 kandidaatklassen, alle major46 (Java1.2),1320 verwijzingen opgelost,
0 ontbrekende leden,0 private-accessfouten,0 onbevestigde verwijzingen en0 ROM-
leesfouten. Auditrapport build/navigation-priority/rom-link-audit.json. Een
onopgeloste referentie laat de audit nu falen (niet als optionele API goedkeuren).
De packagebuilder vereist audit van exact dezelfde JAR met alle foutlijsten leeg
en neemt rapport+hash op in ZIP/manifest. ASM-stackcontrole en exacte hooktellingen
slagen. Drie Java policy/runtime-tests en package/rollback/oneboot-tests opnieuw
gehaald. Dit is sterker offline bewijs; GEEN bewijs van J9-start, HMI-boot of
fysieke omschakeling. De eerdere OOM van controle-JVM blijft onbevestigd qua oorzaak.

Laatste ZIP SHA
d39d212fa35733a183a447aaed73133d7f46eb77c7fdfea2ecd776009f992577
(build/porsche-navigation-priority-MU1417-test.zip). Nativefaf28f9c behouden en
bevat de bevestigde startupfix. Oude RAM-stage/JARc81b7a2 en scripts op unit horen
NIET bij deze laatste build. Volgende auto-sessie eerst nieuwe bestanden/hashes
overdracht en aparte J9-linkcontrole; geen oude installer automatisch gebruiken.
Voorrang is nog steeds niet geinstalleerd/geactiveerd, werkende baseline blijft.

Offline opdrachten:
python build-tools/verify_priority_rom_links.py --recovery-root <bestaande-mu1417-recovery>
python build-tools/build_navigation_priority_package.py
python -m pytest -q tests/test_navigation_priority_policy.py tests/test_navigation_priority_runtime.py
(voor die Java-tests JAVA_HOME op bestaande JDK zetten).
Docker qnx65-armv7:4.9: python3 tests/navigation_priority_transaction.py.


## LOPEND - Porsche-routevoorrang, 17 november 2026; gebruiker uit auto

Gebruiker vroeg de voorbereide voorrangsfunctie. Lokale kandidaat bijgewerkt om
DE HUIDIGE startupfix te behouden: prepare_navigation_priority_native.py genereert
nu eerst build/context-startup/porsche_unit.c en bouwt daarop voort. Package
baseline_window is6e7fcdaa, niet meer41414ee5. Java-baselines59842f9e/a24db7e9
zijn gelijk gebleven. Nieuw native artifactfaf28f9c3997766962feb3cdf4f8b28a44451cf839db6650a997b16a95a82995;
Java artifactc81b7a2befaf198720fe976dd6e8bd9d57761e75d65291a7033677a195728663.

3 host-Java tests geslaagd (policytransities en runtime/writerinterleaving),
native gate Linux-C-test geslaagd, legacy-ASM-verificatie/hooks en QNX-build
-Werror geslaagd. Opt-out van de gepatchte guidance slaagt tegen bestaande
RouteGuidanceTextFixture met alleen de guidance/runtimeklassen voor de hoststubs.
Hele candidate-JAR voor hoststubs plaatsen geeft ontbrekende OEM-interfaces;
dat is geen geldig hostfixture-classpath. tests/navigation_priority_transaction.py
blijft slagen met de nieuwe startupbaseline (corrupt input, rollback, oneboot,
volgende-boot-terugval en exact herstel naar6e7fcdaa/5a7f5a08).

RAM-stage op unit /ramdisk/cw-navigation-priority-20261117 (verdwijnt na reboot),
alle zes bestanden via tijdelijke RAM-ontvanger22110 met correcte hashes overgezet.
Echte QNX-ksh-syntax goed. Installer tweemaal geprobeerd, maar verplichte aparte
J9-linkcheck faalde VOOR mount/schrijven met JVMEXEX015E startup Out of memory.
Eerst Xmx12m, daarna Xmx32m; ook32m faalde. GEEN prioriteits-JAR, aangepaste LSD,
pending-marker of nieuwe native ELF geinstalleerd. Pending-bestand gecontroleerd:
ontbreekt. Bestaande kaart/guidance/startupfix blijven6e7fcdaa/A033/5a7f5a08.
Gebruiker wilde uit de auto: geen verdere unitacties of reboot gedaan en expliciet
gezegd dat vertrekken kon. Niet opnieuw een zichtbare proef starten zonder nieuwe
stilstandbevestiging. Voorrang is nog NIET actief, NIET fysiek bevestigd.

Onderzoek controle-JVM: historische werkende helper staat in
mqb-backend-private/.tmp/porsche-carplay-recovery/run_link_test.py en
java-link-verified48.txt. Die gebruikt minimale LD_LIBRARY_PATH
/ifs/jre/bin:/armle/lib:/armle/usr/lib:/eso/lib en absolute bootclasspath-prefixen.
Nieuwe link-check.sh gebruikte extra /mnt/app-librarypaden en relatieve prefix.
Lokaal aangepast naar historisch minimale librarypath en absolute $PWD-prefix;
Xmx32m en20s grens behouden. Dit is een nog ONBEVESTIGDE reparatie van de
controleomgeving, niet een bewezen oorzaak van OOM. Die aangepaste scripts zijn
NIET opnieuw naar de unit overgezet/getest. Geen extra geheugenverhogingen gokken.

Laatste lokale ZIP build/porsche-navigation-priority-MU1417-test.zip SHA
36a50724335813f34740ab21ace01e693129cf5d16cd416b84b926c7855a93c8;
installer/linkscripthashes daarin verschillen dus van de RAM-stage van de unit.
Controleer manifest, draag bijgewerkte scripts over en verifieer hashes opnieuw.
Volgende stap bij beschikbare auto: in aparte korte JVM eerst -version/probe met
exact historisch librarypad controleren; daarna RuntimeLinkProbe (zonder OEM-
initializers), pas na volledige LINK_PASS de oneboot-installer laten doorgaan.
Geen linkcheck omzeilen. Bestaande oneboot-native/Java-kandidaat nog functioneel
controleren op idle-event bij start en Porsche-route start/stop/reconnect. Aankomst-
presentatie is alleen via originele inactive-callback gekoppeld, geen verzonnen
holdtimer. iPhone-route/audio blijft op achtergrond; alleen tellerbron wordt gekozen.


## FYSIEK BEVESTIGD - startupvariant na PCM-herstart, 17 november 2026

Na nieuwe expliciete stilstand/herstartbevestiging RCC-reboot uitgevoerd. Nieuwe
receiver1675370, worker1966203. Nieuwste native startupvariant6e7fcdaa is geladen:
CARPLAY_CONTEXT_DEFERRED free-window=78 t_ms=28870;
CARPLAY_CONTEXT_PREPARED t_ms=34573;
CARPLAY_ACTIVE display=1 context=70 size=800x480 t_ms=37241.
Verse video/ready-leases aanwezig, slechts een workerstart, geen restartlus in de
opname. Apple-guidance main13/direction64 bij cursor4 met teruglopende afstand.
Gebruiker bevestigde expliciet dat kaart EN routeaanwijzingen zichtbaar zijn.

Gemeten kaartactivatie bij deze PCM-herstart:37.241s na boot, circa18s na iPhone
IdentificationAccepted op t19. Eerdere PCM-herstart had identificatie op t49 en
kaartactivatie tussen61..72; de telefoon kwam nu dus ook vroeger online. Schrijf
niet de volledige end-to-end tijdwinst automatisch toe aan de startupvariant.
De nieuwe ordening (worker voor contextcontrole, daarna strikte activatie) is
wel fysiek succesvol doorlopen. Een nieuwe volledige ruststart met deze variant
moet nog worden gemeten; de eerdere126s-meting was met de oude41414ee5-versie.
Permanent geinstalleerde native variant en Apple-fix blijven staan. Geen commit
of push uitgevoerd voor deze sessiewijzigingen.


## NIEUWSTE INSTALLATIE - context-startup-variant, 17 november 2026

Gebruiker vroeg ruststartfix en expliciet 'zet er maar in'. Native kandidaat is
geinstalleerd op schijf, zonder de lopende supervisor/renderer te stoppen en
zonder reboot. Exacte nieuwe cw-window-candidate SHA:
6e7fcdaad2aef40cf9381f6a08374b58501044d63d091ad64957921f8a426d9f.
Backup controls-v15/before-context-startup-20261117/cw-window-candidate is exact
41414ee595c11b9417c76cea06a8209f4cceb02d395c61a546dd000b65705cce.
Beide hashes teruggelezen; installer remount -ur geslaagd. DIO2441337,
supervisor2523258, workers3149952/3149954 bleven draaien met verse 800x480-ready.
Dus op dit moment draait de oude in-memory versie nog; nieuwe ELF wordt bij een
volgende receiver/supervisorstart geladen. GEEN fysieke validatie van nieuwe
startupvariant claimen; tijdwinst na volledige ruststart nog te meten.

Implementatie: build-tools/prepare_context_startup.py genereert een afzonderlijke
kopie naar build/context-startup/porsche_unit.c. Baseline native/porsche_unit.c,
porsche_dm.c, capture, Java, guidance en alle processing-boundarybestanden zijn
ongewijzigd. QNX-build: build-tools/build_context_startup_qnx.sh.
Referentiepatroon: LuKa carplay_monitor.sh start renderer onafhankelijk van het
later omschakelen van de presentatiecontext. Kandidaat start decoder/renderer op
een vooraf geverifieerde vrije laag78 zonder eerst gc/prepare_context af te wachten.
Een bestaand of corrupt ownerrecord blijft vooraf blokkeren als dat niet veilig
als vrij kan worden aangemerkt. Bestaande vensters volgen de oorspronkelijke
strikte controle. Na bruikbare pixels worden de oorspronkelijke context-,
eigenaarschap- en compositiecontroles alsnog afgedwongen VOOR ready/switch.
Bij wachten blijft OEM zichtbaar en wordt een gezonde worker behouden.
Dit kan de opstartafhankelijkheid doorbreken; het bewijst nog NIET welke specifieke
gc/ownerconditie tijdens de gemeten ruststart faalde of hoeveel tijd dit bespaart.

Toegevoegd: CARPLAY_CONTEXT_DEFERRED, CARPLAY_CONTEXT_WAIT reason=query/report/
layout/owner-record/live-owner/owner-write, CARPLAY_CONTEXT_PREPARED en monotone
milliseconden op CARPLAY_ACTIVE. Daarmee volgende start exact(er) volgen.
De aanvankelijke gedachte dat de numerieke gc-kolom flags was, is VERWORPEN:
alle 165 OEM-records hadden exact dat aantal lagen. Er is geen parserwijziging
voor die onjuiste hypothese gedaan. Eigenaarcontrole is NIET uitgezet/verruimd.

Tests: tests/context_startup_runtime.py compileert echte baseline en kandidaat-
supervisor, stubt alleen de GPU-worker en gebruikt echte begrensde dmdt-subprocessen.
Toont: baseline wacht zonder worker bij gc-blokkade; kandidaat warmt eenmaal op,
laat OEM staan, geeft geen ready voor contexttoestemming, weigert andere levende
eigenaar, schakelt na vrijgave en herstelt OEM bij disconnect. Dit test geen GPU
of echte bootduur. QNX-build met -Werror geslaagd. Installer
unit/install_context_startup.sh met tests/context_startup_transaction.py getest:
corrupt payload geweigerd voor mount, backup, atomische swap, rollback na fout
NA swap, read-only remount. Gepinde processing-boundarytest blijft slagen.

Overdracht: raw Telnet-upload bleek onvolledig (hashcontrole voorkwam installatie).
Daarna bestaande unit-query/ram_receive.c helper gebruikt: tijdelijke RAM-ontvanger
op bestaande debugpoort22110, eenmalige random token, max1MiB, alarm20s. Beide
bestanden snel en exact overgezet; listener sluit na 1 overdracht. Geen FTP- of
firewallconfig gewijzigd. Kleine helper vooraf betrouwbaar gecomprimeerd via
.tmp/unit_console.py --upload geladen. Gebruik voortaan dit bekende RAM-pad voor
binaries; raw telnet_push --binary niet als betrouwbaar presenteren.

Pakket: build/context-startup-MU1417-20261117.zip met kandidaat, install.sh en hashes.
Dit is een zelfstandig native updatepakket, geen generieke SD-menu-update.
Volgende stap: afgesproken nieuwe start, controleer log plus fysieke kaart en
vergelijk volledige ruststart. Niet spontaan herstarten tijdens rijden. Voor exact
herstel atomisch de geback-upte41414ee5 ELF terugzetten; Apple-fix/Java/capture
hoeven daarvoor niet gewijzigd te worden.


## RUSTSTART WAARGENOMEN - 17 november 2026

Gebruiker meldde een start vanuit rust. Nieuwe receiver2441337 en supervisor2523258;
RGI IdentificationAccepted op t60, guidance geldig vanaf t66 (Apple-labelwissel
behoudt nu manoeuvretype/hoek). Rond t86..91 nog geen ready/context/ownerbestand;
supervisor herhaalde CARPLAY_CONTEXT_NOT_AVAILABLE en had geen videoworker.
Daarna CWCT1 timestamp126 original72; worker3149952 en CARPLAY_ACTIVE verschenen.
Bij de volgende volledige controle verse CWRD1 epoch4356 timestamp310 800x480.
Dus schermvoorbereiding kon pas op 126s na boot, tegenover 61s bij de eerdere
PCM-herstart. Het exacte eerste zichtbare frame is NIET getimestamped; presenteer
126s niet als exacte kaartverschijntijd. Geen automatische workerherstartlus gezien.

Deze opname lokaliseert wachten in prepare_context (gc-query/controle/eigenaarschap),
maar de generieke foutmelding onderscheidt querytimeout en afgewezen registratie
nog niet. Geen configuratie of draaiende CarPlay-processen gewijzigd/herstart.
Een afzonderlijke handmatige read-only dmdt gc-query met stdio-preload liep vast
met 'proxy is DEAD'; eigen diagnostiekproces3629191 na verificatie van commandline
met TERM beeindigd en afwezigheid bevestigd. Dit is GEEN bewijs dat de supervisor
precies dezelfde fout kreeg. Vermijd onbeperkte nieuwe handmatige dmdt-queries.

Volgende reparatiestap: prepare_context-diagnostiek met monotone tijdstempels en
onderscheid query/parse/context/owner (afzonderlijk afgebakende startupwijziging),
vergelijken met referentie en OEM-coldbootregistratie. Niet blind context70 wissen
of overnemen zonder controle op lagen/eigenaar. Startupvertraging nog niet opgelost.


## LIVE NA HERSTART - 17 november 2026

Na expliciete stilstand- en herstartbevestiging RCC-reboot uitgevoerd. Telnet werd
door de unit verbroken en kwam terug met verse RAM-state. Nieuwe receiver2363513,
supervisor2437242, decoder/renderer2592892/2592899. Nieuwe logging bestaat nu echt
in /ramdisk/cw-link-probe-20261102/cw-carplay-live-v14.log en meldt een workerstart,
gevolgd door CARPLAY_ACTIVE display=1 context=70 size=800x480. Verse ready:
CWRD1 epoch338 timestamp72 800x480. In deze korte opname geen preflight-failure of
herhaalde workerstarts. Dit is een PCM-herstart, GEEN volledige ruststartproef.

Live RGI wisselt t51..54 opnieuw Apple Maps -> gelokaliseerd Apple Kaarten ->
Apple Maps, maar heeft daarna rawType11, main13 en twee gecachte rijstroken;
Java publiceert maneuver13/0 en phase2. Eerder was rawType=-1/main1 na dezelfde
labelwissel. Daarmee is behoud over de labelwissel op de unit bevestigd. Het
actuele type11 zonder afslaghoek levert legitiem een rechtuitdescriptor; nog
niet alle afslagtypen of een volledige rit fysiek bevestigd. Gebruiker bevestigde na deze herstart expliciet: kaart EN routebegeleiding
zichtbaar. Dit is fysiek bevestigd; ruststart en volledige manoeuvreverwerking
tijdens een rit blijven afzonderlijk te controleren. Parser en starterreparatie zijn nu geladen. Oude tekst
'NOG NIET in nieuwe sessie' hieronder betreft de fase voor deze herstart.


## ACTUEEL 17 november 2026 - Apple-bronlabel gerepareerd, logging voorbereid

Fysiek onderzocht via Telnet, zonder reboot of processtop. In dezelfde actieve
Apple-sessie wisselde source_name op t=1496 van het gelokaliseerde Apple Kaarten
(met afwijkende spatie) naar Apple Maps. De bestaande parser behandelde elke
naamswijziging als een andere app en wiste de manoeuvrecache. Live CWRG5 had
vervolgens cursor 0..3, positieve telling/afstanden, maar rawType=-1 en main=1;
Java publiceerde Follow. Vanaf cursor 8 kwamen weer echte afslagdescriptoren.
Waarom iOS juist die payload opnieuw stuurde is zonder raw capture onbevestigd.

Reparatie native/porsche_rgi.c: uitsluitend bekende Apple Maps/Apple Kaarten
aliaslabels (ASCII, NBSP en UTF-8 NBSP) delen bronidentiteit. De actuele labeltekst
blijft bijgewerkt; echte appwissels zoals Google Maps wissen nog steeds de cache.
Ontvangsthook, Java, zoom, renderer en alle gepinde processing-boundarybestanden
zijn ongewijzigd. De afzonderlijk aangetoonde count-only/selectiebug is NIET in
deze reparatie meegenomen; verwar die niet met de live gevonden bronwissel.

Opstartdiagnostiek: actuele supervisor PID8388737 had stdout/stderr op /dev/ser1.
Het verwachte cw-carplay-live-v14.log ontbrak; persistente renderer.log hoorde bij
een oudere receiver. Daarom is de oorzaak van de gemelde trage ruststart nog niet
bewezen. unit/carplay_receiver_start.sh stelt nu inherited stdout/stderr naar dat
logbestand in, met exec-fallback als het log niet geopend kan worden. Werking op
de daadwerkelijke QNX spawn-keten moet bij de volgende receiverstart worden
gecontroleerd (pidin fds + log); niet als fysiek opgelost presenteren.

Geinstalleerd via unit/install_source_alias_repair.sh, marker
SOURCE_ALIAS_REPAIR_INSTALLED_RESTART_REQUIRED. Beide doelhashes teruggelezen:
- cw-rgi.so a033051e84926c9a6912970771f5dbb5ee7dd124f6953898c4fdaf9f143e000e
- cw-carplay-start 19728746c841f472e37df42aa1ff617d3bca2f37fefac35486e5d0b03d4a8118
Backup: controls-v15/before-apple-source-20261117/ bevat native c917554d en
starter f58eba1a. Remount -ur geslaagd; DIO bleef PID8319100. Geen herstart,
geen kill, geen wijziging van confirmed-markers. Bestanden staan permanent op
schijf, maar de reparatie is NOG NIET fysiek in een nieuwe sessie bevestigd.
Nieuwe mm-ipod start laadt parser; nieuwe receiverstart laadt starterdiagnostiek.

Lokaal geslaagd: tests/test_rgi_source_alias.c, bestaande RGI/lifecycle-tests,
4536 referentiemappinggevallen, receiver_bootstrap_host.py (same PID, herhaalde
exec, disabled fallback), QNX crosscompile van uitsluitend RGI, QNX ksh-syntax,
receiver_bootstrap_transaction.py, source_alias_transaction.py en gepinde boundary.
Artifact: build/apple-source-repair-MU1417-20261117.zip, zelfstandig herstelpakket,
geen generieke SD-menu-integratie. Installatie heeft hashcontroles en rollback.

Volgende stap: na normale nieuwe start Apple-route vanaf eerste manoeuvre
controleren; log moet type/cursor behouden over gelokaliseerde bronlabels. Controleer
of supervisor-uitvoer nu in het log komt en meet een echte ruststart. Geen nieuwe
transportexperimenten of restart zonder stilstandbevestiging. De eerdere lokale
navigation-priority-kandidaat is nog steeds NIET op de auto geinstalleerd.


Laatst bijgewerkt: 17 november 2026

## NIEUWSTE LOKALE WERKSTATUS - routevoorrang-kandidaat gereed voor gecontroleerde proef

Gebruiker vroeg een solide oplossing om te testen. Geen unitverbinding, upload,
installatie, bevestiging of herstart gedaan bij deze opdracht. Live blijft de
bevestigde kaart/guidance/logo-basis van de vorige secties.

Afzonderlijk pakket: build/porsche-navigation-priority-MU1417-test.zip
SHA256: 717e4a20010edd3948606e4a8942491f20cecac9268bb2f8cca8ba1e9197fd90
Dit is geen SD Online Menu-overlay; eigen map op SD of via bestaand RAM-pad.
LEESMIJ-TEST.txt en manifest zitten in de ZIP; geen automatische activering.

Implementatie in optional/navigation-priority plus aparte builders; bestaande
java/native/unit-broncode blijft bytegelijk aan de beschermde baseline. De nieuwe
builder patcht alleen aparte kopie?n: DSI-update entry, ClusterService-return,
guidance apply/clear/poll,12 BAP/synchronized-methoden, ready-gate en zoomqueue-
flush. Geen nieuwe constructorthread; de bestaande guidance-worker publiceert
CRC-beveiligde producergebonden3s-status naar een opt-in native gate. Native
blijft decoderen, laat OEM zien bij routevoorrang en bevestigt echte uitvoer.
De logo-helper gebruikt de gekopieerde ready-gate en volgt zo dezelfde keuze.

Artefacts:
- Java: c81b7a2befaf198720fe976dd6e8bd9d57761e75d65291a7033677a195728663
- Native: 0dcb8401e141bdf1eeb2d03fb108be5c1a267545aeace66818d2670948fa1b4c
- Teststarter: 1e642718e9caad87ff350160cbc9877e214cd2a188600892d622d412691d43f8
Baselineguards: native41414ee5..., starter5a7f5a08..., logo-JAR59842f9e...,
guidancea24db7e9..., capturec0208032... en dispatcherklasseb2857648....
Originele capture/guidance/logo-JARs worden niet vervangen door de installer.
Backup native/LSD: controls-v15/before-navigation-priority-20261116/.

Install.sh verifieert hashes en draait eerst link-check.sh: aparte echte J9
met12MB heap, -Xverify:all, geen OEM-initializers en20s-time-out met eigen-child-
opruiming. Dit is nog NIET op de echte unit uitgevoerd. Bij mislukking geen
remount of installatie. Daarna transactionele installatie en one-boot-ticket.
Bij volgende HMI-start zonder ticket: bevestigde Java-baseline en RAM-gate uit;
native kandidaat blijft dan inert op app. Restore.sh herstelt de exacte oude
native/LSD-bestanden en vereist daarna herstart. Geen permanente bevestiging
voor deze nieuwe prioriteitsfunctie gebouwd/geactiveerd.

Controles geslaagd: 2.304 policytransities; echte runtime-adapter met threads en
CRC-records; bestaande guidance-boundary en logo-lifecycle (5 pytest-tests);
Linux-C-gate met echte wire/CRC/freshness; QNX ARM -Werror; ASM/legacy-bytecode;
bestaande RouteGuidanceTextFixture tegen de gewrapte guidance (optie uit);
pakkettransactionstest inclusief corruptie, renamefout, terugval,1 prefix en
volledig herstel. Scripts ksh-syntax in toolchain goed. Dit is geen fysieke
validatie of echte-J9-linkbewijs.

Volgende stap: docs/NAVIGATION_PRIORITY.md en optional/navigation-priority/
LEESMIJ-TEST.txt lezen. Bij afgesproken stilstand kandidaat in RAM/SD, echte
J9-linkcontrole, pas daarna one-boot-installatie en expliciete herstartbevestiging.
Test CP -> nieuwe OEM-route -> stop -> CP, USB tijdens OEM-route, zoom/logo en
oude veldresten; aankomst apart beoordelen. In deze kandidaat betekent vrijgave
het einde van de originele inactive-update; een aparte aankomstpresentatieduur
is niet bewezen. Geen iPhone-routestop/audio-overname. Reeds verstuurde iOS-
zoom kan niet teruggenomen worden; nieuwe/queued Java-zoom wordt geblokkeerd.
Niet gecommit/gepusht. Oudere 'alleen policy'-secties zijn historisch.


## NIEUWSTE LIVE STATUS ? CarPlay-logo-onderdrukking permanent bevestigd

16 november 2026: gebruiker zag CarPlay-kaart zonder Google-logo en vroeg
expliciet permanent activeren. `unit/confirm_satellite_logo.sh` uitgevoerd na
live hashcontrole en QNX-syntaxiscontrole. Resultaat
SATELLITE_LOGO_CONFIRMED_NO_REBOOT. Bevestiging teruggelezen uit
`/mnt/persist/connectwow-carplay/satellite-logo-probe/confirmed`.

Actuele LSD-hash5a7f5a087afb6699f2ba5ecb2297e2235f403db0e591164dd0749178dda2a368.
Aparte logo-/zoom-JAR59842f9e68060680a93dcbb2eba6dbeb184dfd1295a626782b832c9905bcf542
wordt bij elke start geselecteerd met property
`connectwow.carplay.satelliteLogo=hide-during-carplay`. Originele zoom-JAR264f4231
blijft aanwezig. Video-/guidancepayloads en hun bevestigingen niet gewijzigd.
Geen nieuwe reboot: lopende proef draaide al met dezelfde fysiek bevestigde JAR.

Backup onder controls-v15/before-logo-probe-20261116/: `lsd.sh` is de baseline93d7fed1;
`lsd-logo-oneshot.sh` is de eerdere proefstarter52e32b89. Hashes gevalideerd.
Generator `build-tools/prepare_satellite_logo_launcher.py` maakt de bevestigde
starter vanuit exact baseline93d7fed1; installatie bevestigt alleen na exact
proefhash52e32b89. Verwijderen confirmed-marker laat volgende start terugvallen
naar oorspronkelijke zoom. Geen automatische herstart of permanent herstel nodig.

Runtime-log v??r bevestiging: view0/carplaytrue, vervolgens view1/carplayfalse,
dan weer view0/carplaytrue. Herstel/onderdrukking werkt dus volgens de log;
alleen afwezig logo tijdens CarPlay is fysiek door gebruiker bevestigd. Langdurige
koude/slaapstart en herstelweergave nog niet fysiek bewezen. Shellfixture bevestigt
herhaald laden, terugval na markerverwijdering en ongewijzigde guidancekeuze.

Deze nieuwste sectie vervangt eerdere one-boot-/niet-ge?nstalleerd-statussen
verderop. Nog niet gecommit/gepusht; generieke SD-profielintegratie blijft open.


## ACTUEEL ? nieuwe video-starter na herstart fysiek bevestigd

Herstart uitgevoerd na expliciete stilstandbevestiging. SI startte de nieuwe
launcher: `RECEIVER_VIDEO_BOOTSTRAP pid=2560121`; dezelfde PID werd de originele
DIO. Capturelog toont geldige AVCC-frames800x480. Supervisor2629754 met
workers2707580/2707586; verse ready `CWRD1 654 85 800 480 c283a0de`.
Guidance native Apple Maps epoch10, afstand91m, Java apply bleef lopen zonder
gemelde fout (route17143m/1320s). Gebruiker bevestigde expliciet:
**Kaart en routeaanwijzingen zichtbaar**. Deze start is fysiek bevestigd;
meerdere USB-reconnects, koude slaapstart en lange duur nog niet getest.
Permanent ge?nstalleerde starter/config en guidance-confirmedmarkers blijven
staan. Geen extra proefmarker nodig voor deze starter. Niet gecommit/gepusht.

16 november 2026: gebruiker meldde kaart weg na de kaartfix en eiste oplossen,
geen terugzetactie. De kaart was kort ACTIVE, daarna stopte eigenaar2842749;
nieuwe OEM-DIO PID8425601 draaide zonder capturebibliotheek en zonder de
bedoelde video-omgeving. Vastgesteld via gefilterde pidin-env/mem en lease/logs;
waarom SI deze eerdere envs niet toepaste is niet bewezen. Guidance bleef lopen.

Nieuwe reparatie: `unit/carplay_receiver_start.sh` expliciet als SI-child
`/mnt/app/eso/bin/apps/cw-carplay-start`; zet video-env en preload zelf en exec't
onmiddellijk de ongewijzigde OEM `dio_manager.cw-stock` met dezelfde PID.
Referentiepatroon: `.tmp/mib2q-carplay-rgi/deploy/smartphone_integrator/carplay_startup.sh`.
Geen nieuwe RX/TX-hook, Java-thread of andere capturebibliotheek.
`build-tools/prepare_receiver_start_config.py` verwijdert alleen de zes eerdere
video-envregels uit SI en wijzigt uitsluitend het CarPlay-executable. Andere
children/watchdogs/USB-instellingen blijven gelijk. Geen rollback uitgevoerd.

Op de unit ge?nstalleerd met `unit/install_receiver_bootstrap.sh`, melding
VIDEO_BOOTSTRAP_INSTALLED_RESTART_REQUIRED. Beide doelhashes teruggelezen:
- starter f58eba1a8fed93dd6e5e521bf46990be0af9b28f0b01b1025c29b2b7a61bc85e;
- SI-config 722b47123494e22b8fa4b4e50b3cce07f5b0399f1f31c7fd5e8f51ff981350d9.
- vorige config e042e65da4f366fef35c700528c7054fcf7f6e38dba23f7c291928895d91cb86
  geback-upt onder controls-v15/before-video-bootstrap-20261116/smartphone_integrator.json.
- Nieuw window41414ee5, capturec0208032, guidancec917554d/a24db7e9 behouden.

Lokaal getest: twee configtests; drie verse exec-starts met dezelfde PID,
expliciete env, argumentbehoud en uitgeschakelde OEM-fallback; installtransactie
op mockfilesystem inclusief weigeren corrupt payload v??r mount, backup en
remount beide partities read-only. Beide scripts ksh-syntax op echte unit goed.
Dit bewijst nog niet dat SI de starter na reboot uitvoert of fysieke reconnect werkt.
Pakket: `build/receiver-video-bootstrap-MU1417.zip`.
Tests: `tests/receiver_bootstrap_host.py`, `tests/receiver_bootstrap_transaction.py`,
`tests/test_receiver_start_config.py`. Transactietest vereist gegenereerde JSON in
`.tmp/map-output-live/`; geen algemene SD-profielintegratie gedaan.

**Eerstvolgende stap:** bij een volgende afgesproken stilstaande proef ??n USB-
reconnect controleren op nieuwe RECEIVER_VIDEO_BOOTSTRAP-PID, verse ready en
fysiek beeld/guidance. Daarna slaap-/koude start en duurtest. Integreer de starter
en exact beperkte configwijziging in SD-profielpackaging voordat een generiek
SD-pakket als bijgewerkt wordt gepresenteerd. De unit is nu fysiek bevestigd;
de algemene SD-profielgenerator bevat deze nieuwe launcher nog niet.


- Aanvullend functienummer 46 DIRECT uit MU1417 bewezen: `AppConnectorNavi.updateDestinationInfo` bevat `getBAPFunctionPropertyFSG(46)` en maakt `DestinationInfo_Status`; serializer `functionId()` retourneert 46. Dump `build/destination-wire.javap.txt`, recoveryhelper `.tmp/recover-destination-wire.py`. Zie referentie-audit voor classhashes. Geen code/pakket/unit gewijzigd voor deze aanvullende verificatie.

## ACTUEEL LIVE — kaartfix eveneens geïnstalleerd en actief (16 november 2026)

Gebruiker vroeg expliciet ‘zet dat ook aan dan’. Map-pakket fc2342e3 op unit
geïnstalleerd na verificatie originele window0cf0e784/capturec0208032/firmwarehash.
MAP_LEASE_REPAIR_INSTALLED_NO_REBOOT, MAP_INSTALL_RC=0. Nieuw live windowhash:
41414ee595c11b9417c76cea06a8209f4cceb02d395c61a546dd000b65705cce.
Backup oude window onder controls-v15/before-map-lease-20261116/. Alleen deze
native window/supervisor vervangen; capture/DIO/HMI/zoom/guidance niet vervangen.

Zonder PCM-reboot alleen bestaande videosupervisor herstart via RAM-script
`/ramdisk/cw-map-output-repair-20261116/restart-map.sh` (lokaal
`.tmp/map-output-live/restart-map.sh`). Oude PID2977919 vóór TERM met pidin geverifieerd
als juiste --run-tool, owner2842749. Nieuwe supervisor7172223, worker7217201;
VIDEO_SUPERVISOR_STARTED en MAP_RESTART_RC=0. Script ksh-syntax0; unsetLD_PRELOAD
met || : (oude QNX-valkuil), geen SIGKILL of mm-ipod/DIO-herstart.

Runtimebewijs: `/ramdisk/cw-link-probe-20261102/cw-carplay-map-fix.log` bevat
CARPLAY_ACTIVE display=1 context=70 size=800x480. Verse CWRD1-record epoch1192,
timestamp459. GuidanceJava liep door (epoch301, route17242m/1380s, fase1);
beide guidance-confirmedmarkeringen teruggelezen en aanwezig. Geen afzonderlijke
fysieke gebruikersbevestiging NA deze kaartoverschakeling, geen duurtest gedaan.

Kaartbinary is permanent op app-partitie geïnstalleerd en bestaande starter verwijst
naar diezelfde tool; toekomstige starts/reconnects horen deze versie te gebruiken.
Niet als fysiek bewezen koude-boot/reconnectfix voorstellen: dat moet nog getest.
Restore naar oude window via restore.sh uit map-pakket; RAM-staging verdwijnt bij
boot, maar app-backup blijft. Geen commit/push gedaan.

## ACTUEEL LIVE — guidance-checklist permanent bevestigd (16 november 2026)

- Gebruiker bevestigde fysiek ‘Kaart en routeaanwijzingen zichtbaar’ en vroeg daarna
  expliciet ‘activeer maar permanent’. Geen volledige timing-/rotonde-/ETA-/arrivalproef
  afleiden uit deze bevestiging: alleen basisweergave en actieve keten zijn gezien.
- Live runtime vóór bevestiging: native/Java ontvangen Google Maps (niet Apple),
  CWRG5-epochs37..46 doorlopend verwerkt, startmanoeuvre rawType11/cursor0 zonder
  geldige manoeuvreafstand, route21km/1620s, lane-records2. Java apply zonder gemelde
  fout. Verse kaartlease800x480. Gebruiker zag kaart EN guidance fysiek.
- Native c917554d...701e2e9 en JAR a24db7e9...d30bf52 opnieuw op unit geverifieerd.
  `guidance-native/confirmed` en `guidance-probe/confirmed` atomair geschreven en
  teruggelezen (‘confirmed’), CONFIRM_SYNTAX_RC=0, CONFIRM_RC=0,
  GUIDANCE_CHECKLIST_CONFIRMED. Script `.tmp/confirm-guidance-checklist.sh`, op unit
  `/ramdisk/cw-confirm-guidance-checklist.sh`.
- Daardoor geen one-boot-terugval meer: bestaande starters laden dezelfde versie
  ook bij volgende boot/reconnect. Geen starter, kaart of zoom vervangen. Geen
  tweede reboot gedaan voor bevestigen. Kaartreparatiepakket nog NIET geïnstalleerd;
  bestaande windowhash0cf0e784 blijft uitgangspunt.
- Vorige bestanden/markers behouden onder controls-v15/before-processing-checklist-20261116;
  handmatig restore.sh uit testpakket beschikbaar. Native/JAR altijd samen herstellen.
- Nog niet gecommit/pusht. Detailacceptatie (afstanden/pijlmomenten/rotonde/lane-layout,
  ETA/tekstadres/stop/arrival) nog niet volledig fysiek bewezen, ondanks permanente
  activering op uitdrukkelijk verzoek gebruiker.

## Guidance-checklist geïnstalleerd als proef — 16 november 2026

Gebruiker bevestigde expliciet: ‘Ja, installeer en herstart nu’. RAM-installer
`/ramdisk/cw-guidance-checklist-20261116/install.sh` uitgevoerd op MMX:
`GUIDANCE_PROCESSING_TRIAL_READY_NO_REBOOT`, `GUIDANCE_INSTALL_RC=0`.
Live hashes teruggelezen: native c917554d...701e2e9 en JAR a24db7e9...d30bf52,
exact volgens checklist-manifest. Backup van vorige bestanden/confirmed-markers
onder `controls-v15/before-processing-checklist-20261116/`. Bestaande installscript
zet pending one-boot; kaart/zoom/starters niet vervangen. RCC-herstart aangevraagd
via bekende mib2_ioc_flash reboot. Boot-/runtime-/schermbewijs nog controleren;
geen confirmed-markers schrijven zonder fysieke bevestiging. Gebruiker gevraagd
na PCM-start CarPlay te verbinden en route in Apple Kaarten te starten.

Runtime na reboot: Telnet opnieuw bereikbaar; Java-guidancelog op uptime32/37s
wacht op `/ramdisk/cw-carplay-guidance.v1`. Java-probe is attempted, native nog
pending (geen native log/telefoonsessie op dat meetmoment). Dit bewijst Java-start,
geen werkende guidance. Gebruiker gevraagd CarPlay te verbinden en Apple-route te
starten; wachten op antwoord/runtime. Geen extra reboot of rollback uitgevoerd.

## Livevoorbereiding na ‘telnet is actief’ — 16 november 2026

- RCC172.16.250.248 verbonden. Originele guidance-native791a8673 en JARfae18ec4 op unit teruggelezen; window0cf0e784 ongewijzigd. Beide guidance-confirmedmarkeringen aanwezig, checklist-backupmap bestaat nog niet.
- Checklist-pakket6bbf751c gecontroleerd en alleen naar RAM gestaged onder `/ramdisk/cw-guidance-checklist-20261116/`: cw-rgi.so, PorscheCarPlayGuidance.experimental.jar, install.sh, restore.sh. Overdracht gecomprimeerd; hashes van uitgepakte payloads op unit exact c917554d/a24db7e9. Geen APP-bestanden vervangen, geen pendingmarker gezet, geen reboot.
- Beide scripts op echte MMX-ksh syntactisch gecontroleerd zonder fout. Huidige RAM had nog geen ready-lease/RGI-log; geen actieve CarPlay-sessie veronderstellen.
- Volgende stap: wachten op bevestiging dat auto stilstaat en gebruiker klaarzit. Dan pas de klaargezette guidance-installer uitvoeren; alleen bij GUIDANCE_PROCESSING_TRIAL_READY_NO_REBOOT + exit0 de afgesproken RCC-herstart. Kaartpakket NIET installeren. Daarna logs en echte routeguidance controleren; geen confirmed vóór fysieke bevestiging.

## ACTUEEL — zeven verwerkingsstappen, ontvangstketen behouden (16 november 2026)

Gebruiker corrigeerde expliciet: guidance-ontvangst/uitvoer WERKTE, alleen inhoud
was fout. Geen vervanging van ontvangsthooks, abonnementen, starters, kaart of
zoom. Daarom alleen verwerking aangepast en lokaal getest, GEEN unitactie.

Volledig voortgangsdocument: `docs/GUIDANCE_CHECKLIST_PROGRESS.md` (zeven stappen,
tests, artifacthashes, fysieke grenzen). Oude 68-regelige matrix is een auditstand;
nieuwere verwerkingstatus staat in dit voortgangsdocument. Geen volledige port van
alle optionele transport/menu/rendererfuncties claimen.

- Stap1 bestaande cursor/prefetchbehoud + count-only clear zonder cachedataloss.
- Stap2 junction_angles en exacte LuKa SideStreets-port, 29484 oraclecases.
- Stap3 distance replay uitsluitend zelfde cursor/type, referentie actionblink
  600ms100/0 laatste20% via BESTAANDE Java-poll, geen nieuwe thread.
- Stap4 lane-eventcache32 met actieve eventbescherming, signed richtingen/countgate.
- Stap5 volgendeweg/signpost via firmware `setTurnToInfo`, huidige straat behouden;
  afzonderlijk bestaand DestinationInfo/BAP46, referentietekstnormalisatie.
- Stap6 absolute ETA via originele HU-klok/UTC->local, snapshotleeftijd meenemen;
  bestaand OEM12/24-uursgedrag. Firmware API-hashes/descriptors gecontroleerd.
- Stap7 stop-/arrivaldeadlines ook zonder vervolgpacket in bestaande Java-readpoll.
  Geen transporttimer of hook toegevoegd. Nieuwe route na arrival reset oude cache.

Interne snapshot **CWRG5** (geen nieuw iAP2-protocol). Native en JAR SAMEN bijwerken;
nieuwe Java leest ook CWRG1..4, oude Java kan5niet lezen. Bestaande field-based
CRC/rename-keten behouden. Eigen guidanceclasses nu9 (4 hoofd/inner +5 sidestreet),
naast bestaande enige OEM-hook ClusterService; geen OEM-dataklassen meegeleverd.

Begrenzing gepind in `tests/fixtures/guidance-processing-boundary.json` (12files);
test en --profilechecklist-builder falen bij wijziging ontvangst/map/startup/V14.
Checkpoint `build/guidance-processing-checkpoint/before-checklist.zip`. Vóór deze
opdracht bewaarde map- en guidance-ZIPs zijn bytegelijk gebleven.

NIEUW, NIET LIVE: `build/guidance-processing-checklist-MU1417.zip`, SHA
`6bbf751cae01f76b206cb289bf9a856925f253a9a328cd930b1ad48be9cf4402`.
Native `c917554dc9027d8d0fc8044dbccf71c1ef7f5689966427b7bf122df86701e2e9`,
JAR `a24db7e9851b736bc4a3def7081de8219ab4f6e9f15a23c6ed644e1b5d30bf52`.
Bouwen met `python build-tools/build_guidance_patch.py --profile checklist` na
native/Java-build/split; standaard presentation-profiel weigert nieuwe payloads
om oude bewaarde presentatie-ZIP niet stil te overschrijven. Oude presentatie/map
pakketten niet opnieuw met huidige broncode genereren alsof het dezelfde build is.

Geslaagd: volledige native ASan/UBSan-suite, QNX-crossbuild, Java/bytecode/fixtures,
echte nativeTLV->CWRG5->JavaOEMmock-keten, 4536mapper/29484sidestreetoraclecases,
21Pythonchecks (1Windows-shellskip), ksh-syntax en echte install/restore-scripts op
mockFS (guidance_package_transaction.py). Dit is GEEN fysieke schermacceptatie.

Volgende stap is fysieke test, alleen na afgesproken moment. Geen unitverbinding,
installatie, reboot, commit of push tijdens deze checklistuitwerking. Behoud oude
workingflow; transport5203/backoff/takeover/extra menus/eigenrenderer NIET door deze
opdracht laten terugkeren. Zie docs voor resterende referentieafwijkingen.

## Systematische guidance-portaudit (16 november 2026)

Op gebruikersverzoek alle guidancefunctiegroepen naast vastgezette LuKa-referentie
(21f5016) en aanvullende Fifthbro-bron (c737650) gelegd. Resultaat:
`docs/GUIDANCE_PORT_MATRIX.md` met concrete bron-/functieverwijzingen en statussen
Ja/Deels/Nee/Anders/Onbewezen. Audit wijzigt geen broncode, pakketten of unit.
Geen nieuwe tests voor deze read-only vergelijking uitgevoerd.

Belangrijk: vorige ‘4536 vectoren’-claim dekt alleen type/richtingmapper,
NIET volledige port. Gevonden expliciete gaten: manoeuvre-junction_angles en
BAP-sideStreets (nu leeg), actionblink, absolute ETA/timezone, zichtbare
volgendeweg/exittekst (wel opgeslagen), count-/maneuver_state/componentvelden,
protocolstop5203 (parser heeft branch maar hook routeert hem niet en zendt geen
stop), beperkte bron/generatie/teardownkoppeling en geen autonome stoptimer.
Oorspronkelijke synchrone RX-send/2s-retry blijft anders dan referentie.
Lanegeometrie deels geport maar niet alle completeness/fallbacksemantiek bewezen.

`GUIDANCE_REFERENCE_AUDIT.md` stale claim van lifecycle-worker/mutex gecorrigeerd
naar huidige passieve RX-tick. Bestemmingsadres/Fct46 blijft lokaal geïmplementeerd;
fysieke plek bij aankomstsymbool onbevestigd. Geef geen volledige-pariteitsclaim
of de indruk dat de matrix een fysieke functietest is.

## Nieuwste referentievergelijking — bestemmingsadres bij aankomst (16 november 2026)

- Gebruiker wees op adres naast aankomstsymbool en eiste directe vergelijking met referentie. Niet opnieuw een mogelijke aparte tekstpopup als vervanging voorstellen. Er bleek een concrete ontbrekende aanroep, niet een onbekend protocol.
- Vastgestelde referentie: `.tmp/mib2q-carplay-rgi/java_patch/com/luka/carplay/rgd/BAPBridge.java`, blok 9 (FctID 46, rond regel 1195): `new CombiBAPNaviDestination("", "", limitUtf8(destination,50), "", "", "", "")`, verpakken in `CombiBAPDestinationInfo`, doorgeven met `updateDestinationInfo`. Label in dezelfde constructorpositie overgenomen; geen zelfverzonnen adresparser. Broncommit blijft `21f501611b0b28dbdeb2849e8443ce90ec9517ff`.
- Exacte MU1417 firmware bevestigt `CombiBAPListener.setDestinationInfo(CombiBAPDestinationInfo)`; die bewaart destInfo en roept bestaande `updateDestinationInfo()` aan. Beide zeven-string/data-wrapperconstructors uit `rom.classes` hersteld en met javap gecontroleerd. Output `build/destination-api.javap.txt`.
- `PorscheRouteGuidance.update` publiceert nu aparte OEM DestinationInfo, ook bij aankomst. `clear` wist dit veld afzonderlijk met retry bij OEM-fout. Huidige-positietekst blijft onaangetast. UTF-8-limiet 50 bytes en surrogate-paargrens volgen referentie. Geen derdeparty renderer of voertuigvreemde HMI-klassen geïnstalleerd.
- Belangrijke bewuste afwijking: LuKa gebruikt elders CurrentPositionInfo/Fct19 voor routegerelateerde tekst en houdt Fct20 leeg. Dat NIET integraal overgenomen: gebruiker had expliciet foutieve huidige positie door volgende straat gemeld. Bestemming loopt hier via exact ondersteunde DestinationInfo/Fct46, huidige straat blijft huidige straat. Fysieke plaats/acceptatie van het adres naast aankomsticoon nog NIET bevestigd.
- Buildinput toegevoegd: `build/porsche-destination-api.jar`, aangemaakt met `python build-tools/recover_destination_api.py --recovery-root "D:/Software Development/Github/mqb-backend-private/.tmp/porsche-carplay-mu1417"`. Vereist eerder beschikbare deps/jxe2jar/rom.classes, downloadt niets. `build.py --destination-jar` optioneel met deze default. Beide classhashes gepind en constructors/aanroepdescriptor in `BuildPorscheHooks.checkApi` geverifieerd. OEM-dataklassen zijn uitsluitend build-/testinput; NIET meegeleverd in guidance-JAR.
- Javafixture draait tegen de daadwerkelijk herstelde bestemmingdataklassen: normaal label, adres tijdens RS=2, huidige positie ongewijzigd, 50 UTF-8-bytes met accenten en surrogate-paar, null/lege bestemming, wissen en retry bij beëindiging getest. Java/legacy-bytecode/cluster/zoomfixtures en 20 Pythonchecks geslaagd (1 Windows-shellskip).
- Guidance-JAR nu `a5176788f8bc3f9bc8a868c5b8f23723395757203da43b8faf102fc53641fccd`. Bijgewerkt `build/guidance-presentation-MU1417.zip`: SHA `29543da0ed7c14c8b55801fa8a175b07523ddbcb188bcb3000a22c81bf913e8c`. Native `1a75449ff62787599fdfd2a4afa517b3e4dd7779770cd5e1430333cf306f2b65` en los kaartpakket onveranderd. Oudere package-/JARhashes hieronder zijn historisch.
- Nog steeds GEEN liveactie/installatie/reboot/commit/push. Alleen lokale voorbereiding. Geen claim dat fysieke aankomstweergave is bewezen.

## Nieuwste lokale aanvulling — kaartuitvoer en aankomst (16 november 2026)

- Gebruiker vraagt na bovenstaande stop uitsluitend voorbereiding van een oplossing; daarna ook de kaartuitvoer oplossen. GEEN nieuwe toestemming voor live installeren/reboot gevraagd of afgeleid. Tijdens deze aanvulling geen unitverbinding gebruikt.
- Lokale kaartcorrectie in `native/porsche_geometry.c/.h`: `cw_geometry_follow_source` leidt een nieuwe bronobservatie af uit eerder gevalideerde displaygeometrie, uitsluitend bij dezelfde PID met vers gecontroleerde bronlease. Originele HMI-record, CRC en TTL blijven intact; expliciet inactieve geometrie wordt niet heractiveerd.
- `native/porsche_session.c/.h`: `cw_session_observe_frame` gebruikt de werkelijke producer-timestamp van de CRC-gecontroleerde pixellease na een blokkerende displayquery. Een herlezing van dezelfde lease verlengt de levensduur niet. Epoch, afmetingen, toekomst/veroudering en bruikbaar beeld blijven gecontroleerd. Ook eerste bruikbare beelden na een lange preflight kunnen activeren zonder willekeurige restart.
- `native/porsche_unit.c`: cached geometrie wordt nu werkelijk bronvers vernieuwd voordat de sessiecontrole haar gebruikt; na preflight opnieuw dezelfde bron/afmetingen controleren; reeds actieve sessie eerst bijwerken met verse pixels; na langzame outputquery nieuwste VIDEO_READY opnieuw lezen en bron verifiëren.
- Extra oorzaak van lease-uitval: DisplayManager-query mocht 4s duren terwijl HMI READY na 3s verloopt. `native/porsche_dm.c/.h` biedt absolute, gedeelde deadlines (`cw_dm_query_until`, `cw_dm_switch_until`); actieve displaycontrole deelt de bestaande 1s-pollcyclus. Normale koude preflight behoudt gewone 4s-queryallowance. Geen heartbeat-/pixel-TTL verhoogd. Werkende capture/launchers niet veranderd in het kaartpakket.
- Tests: native ASan/UBSan-suite geslaagd, sessie nu 178 checks; nieuwe `tests/test_dm_deadline.c` met echt vertraagde mocksubprocess; QNX ARM-crossbuild geslaagd. 20 relevante Python-tests passed, 1 Windows-shelltest skipped. QNX-toolchain-ksh syntax van kaartinstallatie/herstel geslaagd. `tests/map_package_transaction.py` voert echte pakketinstallatie en restore tegen geïsoleerde mockunit uit: corrupte payload geweigerd vóór mount, backup/restore en RO-remount geslaagd, capture ongewijzigd. Dit is geen fysieke QNX- of schermvalidatie.
- Nieuw afzonderlijk pakket: `build/map-output-repair-MU1417.zip`, SHA256 `fc2342e3fa679e220a2d781f71dd2cc61ebfa01f130e6e7a1ca44f4a0d2c886b`, gebouwd door `build-tools/build_map_output_patch.py`. Enige binaire payload `cw-window-candidate`, SHA `41414ee595c11b9417c76cea06a8209f4cceb02d395c61a546dd000b65705cce`. Vereist exacte teruggezette window/capture/HMI-hashes. Backup/restore inbegrepen; geen automatische herstart. Native vervanging is NIET one-boot; gebruik restore.sh bij mislukte fysieke proef. Pakket is NIET geïnstalleerd.
- Guidancepakket en hashes in volgend blok blijven ongewijzigd. De parser bevat rotondehoek/verkeerszijde-mapping, 4536 onafhankelijke referentiegevallen incl. negatieve hoeken. Correcte fysieke pijlpositie nog onbevestigd.
- Aankomst precies formuleren: expliciet iOS RS=2 publiceert main_element=3, geen lanes, resterende tijd/afstand nul; Java gebruikt de bestaande BAP-manoeuvredescriptor en wist daarna guidance. Prefetched aankomst op >70m wordt niet als bereikt getoond. Er is GEEN aangetoonde aparte OEM-tekstmelding ‘Bestemming bereikt’; geen tekstpopup of spraakbericht beloofd/geïmplementeerd. Timing zonder RX-traffic blijft eerdere freshnessbeperking.
- Resterend: geïsoleerde fysieke validatie van elk pakket na nieuwe gebruikersopdracht. Niet stellen dat alle opstart-/USB/contextproblemen definitief opgelost zijn: alleen bovenstaande fouten zijn lokaal gereproduceerd en gecorrigeerd. Eerdere experimentele capture/supervisor-startcode nog dirty en buiten beide pakketten.

## ACTUEEL — gebruiker heeft liveproeven gestopt; alleen lokaal verder (16 november 2026)

Dit blok heeft voorrang op de historische proefstatus hieronder.

- Gebruiker corrigeert terecht de scope: guidance werkte fysiek; onjuiste manoeuvre/timing/positie was het probleem. De nieuwe ontvangst-/TX-hook was een regressie en mag niet als bewezen reparatie opnieuw worden geactiveerd.
- Laatste TX/video-proef: native `7b1384d3b384a5a54cb213948bbd3f6204f4114c0b3545227cfd9dd914d17c21` stuurde 5200 met rc=0, maar mm-ipod startte herhaaldelijk opnieuw (o.a. uptime 63, 68, 74, 81, 85, 90, 110, 127); geen bruikbare guidance en geen ready-lease. Gebruiker bevestigde dat ook CarPlay op het centrale PCM ontbrak. Rc=0 bewijst dus GEEN werkende keten. Precieze oorzaak niet vastgesteld; eerdere ACK-deadlockhypothese verklaart niet alle uitval.
- Eerst native trial uitgeschakeld en mm-ipod gestopt. Daarna herstel uitgevoerd, nog voordat de gebruikersinstructie ‘laat het maar staan’ binnenkwam. Geen reboot of andere unitactie meer na die instructie. Laat de auto nu met rust; nieuwe lokale kandidaat NIET installeren zonder nieuwe gebruikersopdracht.
- Op schijf teruggezet en hashes teruggelezen: native `791a8673bf198599fd261d6cdfd85f256bdc27537a072b045ee101e57e77d31e`; guidance-JAR `fae18ec437ea7b479777859df649c28a8becfdc7b33b4cb2c7e1e385aaeeadbd`; capture `c020803207a59ac438e2ffe526110ffcb7294cac86236fcf1cb96da9eca3f847`; window `0cf0e784063396004f65d71195649815e467f197a1a9dc2aeb66506c4d412afa`. Originele native/java confirmed-markers uit backup hersteld, pending en RAM-trial verwijderd. `/mnt/app` read-only. Marker `PREVIOUS_GUIDANCE_RESTORED`. Fysieke werking na dit herstel en vervanging van de reeds in geheugen geladen JAR zijn NIET gecontroleerd; daarvoor is later een afgesproken herstart nodig.
- Backups: `controls-v15/guidance-before-reference-20261116` bevat oorspronkelijke native/JAR/markers; `controls-v15/before-video-tx-repair-20261116` bevat oorspronkelijke video/capture en de EERSTE mislukte native. Die laatste cw-rgi.so is GEEN werkende guidancebaseline. Herstelscript lokaal `.tmp/restore-previous-guidance.sh`.

### Klaargezette, smallere kandidaat — nog NIET op de auto

- `native/porsche_rgi_hook.c` is teruggebracht tot exact transport van commit `288175f`, met slechts passieve `cw_rgi_tick` op bestaande RX-traffic toegevoegd. Geen nieuwe TX-callback, mutex, timerthread of constructorthread. De verworpen proefcode/fixture is lokaal bewaard onder `.tmp/rejected-tx-trial-20261116/`.
- Parser `native/porsche_rgi.c/.h` en guidance-Java behouden de referentiecorrecties voor actuele cursor, mapping, afstand, rijstroken en lifecycle. CWRG4 vereist de bijpassende JAR. Deze selectie-/presentatiecorrecties zijn lokaal getest, NIET fysiek bevestigd.
- Belangrijke grens: oorspronkelijke synchrone RX-send blijft bestaan. Terugkeer naar werkende transportcode is geen bewijs dat dit pad onder alle omstandigheden veilig is. Stop/aankomst-timers verlopen passief op RX-traffic; zonder verkeer geldt Java freshness-fallback. Geen nieuwe thread om precieze timers af te dwingen.
- Buildscript `build-tools/build_guidance_patch.py` levert `build/guidance-presentation-MU1417.zip` (SHA256 `bfd1d221fc717dbd429c332f7f270bf3df49cc53c0a8dc4c0c3089e523aa32aa`). Alleen `cw-rgi.so`, guidance-JAR, manifest, installatie/herstel en LEESMIJ. Geen display-, zoom-, menu-, configuratie- of launcherpayload. Geen automatische reboot.
- Kandidaat native SHA `1a75449ff62787599fdfd2a4afa517b3e4dd7779770cd5e1430333cf306f2b65`; JAR `8b82136fdc41618f18579d5a6264aae1661ab36527e0c4ae3331b941d3d9b4f6`.
- Installer accepteert uitsluitend exacte baseline native/JAR plus confirmed-markers, maakt backup, verifieert staging, zet one-boot pending en remount RO. Scripts met QNX-toolchain-ksh syntactisch gecontroleerd. Transactionele foutpaden niet op echte QNX geïnjecteerd.
- Validatie: volledige native ASan/UBSan-suite incl. 4536 onafhankelijke mappinggevallen, lifecycle en baseline packetownership; QNX-crossbuild; Java-build/bytecode/fixtures en split; 20 relevante Python-tests geslaagd, 1 Windows shelltest skipped (eerder afzonderlijk op Linux uitgevoerd). ZIP-integriteit en payloadhashes gecontroleerd. Dit bewijst geen fysieke acceptatie.
- Overige eerdere video/supervisorwijzigingen zijn nog dirty en NIET onderdeel van dit pakket. Brede SD-builder niet gebruiken alsof die alleen de guidancewijziging bevat. Er zijn GEEN nieuwe commits/pushes.

### Eerstvolgende stap

1. Nu uitsluitend lokale review/voorbereiding; geen unitverbinding of reboot nodig.
2. Bij nieuwe toestemming eerst de herstelde baseline fysiek bevestigen na afgesproken boot. Niet combineren met nieuwe video-/zoom-/opstartwijzigingen.
3. Dan uitsluitend guidance-pakket als one-boot proef: centrale CarPlay, tellerkaart, actuele manoeuvre versus iPhone, afstand, rijstroken/positie, appwissel, stoppen/aankomst controleren. Een verzonden 5200 en geslaagde tests niet als gebruikersbevestiging voorstellen.
4. Bij uitval direct de twee oorspronkelijke guidancebestanden herstellen, geen nieuwe transportproef tijdens dezelfde praktijktest.

## KRITIEK — laatste liveproef teruggetrokken; CarPlay fysiek hersteld

- Gebruiker bevestigde CarPlay zichtbaar en USB opnieuw verbonden/route gestart, maar geen nieuwe guidance. Na reconnectcorrectie bleef native 0x5200 mislukken en gebruiker meldde vervolgens CarPlay niet werkend.
- Concrete firmwarebevinding: MU1417 `link_send_raw_message` VA `0x113a8`, grootte `0x11c`, roept `link_send_pkt` op `0x1105c` aan; daarin staat `link_wait` (onder meer call op `0x112ac`). Onze `receive_hook` roept die synchroon aan vanuit de ontvangstthread en nu ook onder state_lock. Dat kan de ontvangst van de ACK en lifecycle-tick blokkeren. Live: IdentifyAccepted, aanvraag wel op iAP2-wire (`5200`), circa 16s later request failed en herhaalde ontvangerstarts. NIET als enkel foutieve succeslogging afdoen. ACK-wachtpad is bewezen, precieze volledige watchdog/crashketen nog niet vastgelegd.
- **NIET opnieuw de huidige native build activeren.** De geslaagde parser-/mapping-/buildtests bewezen de echte transporthandshake niet. Eerst een correct asynchroon verzendpad uitwerken met bewezen contextlevensduur en teardown (geen losse thread met een ongecontroleerde, mogelijk vrijgegeven link-pointer). Geen nieuwe pointer-/vtable-aanname op de live auto.
- Herstel uitgevoerd: `/ramdisk/cw-guidance-native-trial` en pending/confirmed voor guidance-native en guidance-probe verwijderd, RCC herstart. Attempted-markers blijven als historie; zonder RAM-trial/pending/confirmed laden wrappers de nieuwe guidance niet. Native/JAR-bestanden blijven aanwezig maar zijn UIT. Zoom/video/bestaande starters behouden; native proefstarter `1b5c...` blijft geinstalleerd maar zonder ticket/marker inactief.
- **Gebruiker bevestigt na deze herstart: 'Ja, CarPlay werkt weer'.** Dat is het nieuwste fysieke bewijs. Nieuwe guidance dus NIET live/werkend/permanent bevestigd voorstellen. Alle eerdere 'geladen' en installed-hashes hieronder zijn historie, geen geslaagde functieproef.
- Eerste vervolg: transportverzending losmaken van receive_hook, context-lifetime/queue/ACK/reconnect aantoonbaar testen, dan pas nieuwe one-boot proef aanbieden. Ook kaart/telleracceptatie, fases, stoppen/aankomst en pijlpositie blijven fysiek onbevestigd voor de nieuwe versie. Geen extra live wijzigingen gedaan na gebruikersbevestiging van herstel.

## Guidancelevenscyclus 16 november — nieuwste lokale status, NIET live

### Installatie op unit 16 november (nieuwste status)

- Gebruiker autoriseerde live zetten. Telnet `172.16.250.248` bereikbaar; bronhashes native `791a8673bf198599fd261d6cdfd85f256bdc27537a072b045ee101e57e77d31e`, guidance-JAR `fae18ec437ea7b479777859df649c28a8becfdc7b33b4cb2c7e1e385aaeeadbd`, HMI-starter `93d7fed1102c20727a24acefbf43380001f5c9ef32319800bcbe74206d13e59e` en OEM mm-ipod `d5af4a342705bd7ac3498a080e24faf5702c6fc2960895f58aa2800268126464` geverifieerd.
- Nieuwe native `0a2cc0578270aa5f43405e011c8a60b1494b055963ddbaba0700886522f47042` en JAR `8b82136fdc41618f18579d5a6264aae1661ab36527e0c4ae3331b941d3d9b4f6` transactioneel geinstalleerd (`GUIDANCE_REFERENCE_READY`, INSTALL_RC=0). Backupmap `/mnt/app/eso/hmi/connectwow-carplay/controls-v15/guidance-before-reference-20261116/` bevat geverifieerde vorige native/JAR en `native.confirmed`/`java.confirmed`. Installatiescript lokaal `.tmp/install-guidance-reference-20261116.sh`, op unit `/ramdisk/cw-install-guidance-reference-20261116.sh`.
- Veilige eerste activatie: confirmed van guidance-native/guidance-probe vervangen door pending, zodat bestaande wrappers de proef eenmalig laden; volgende boot valt zonder nieuwe bevestiging terug naar OEM-guidance. Zoom, display, starters en serviceproviders niet gewijzigd. `/mnt/app` na succesvolle installatie read-only. Niet als permanent bevestigd voorstellen voordat functieproef slaagt.
- RCC-herstart aangevraagd via `on -f rcc /usr/apps/mib2_ioc_flash reboot`; runtime/bootbewijs hieronder aanvullen. SD-pakket nog niet bijgewerkt. Geen commit/push van deze nieuwe lokale wijzigingen.
- Runtime na deze herstart: HMI/J9 draait met de losse zoom- en nieuwe guidance-JAR op bootclasspath; native mm-ipod logt `Porsche MU1417 mm-ipod RGI table preload active`, `dispatch tables active` en `iOS IdentificationAccepted` op uptime 50/51. CWRG4 disconnect/inactieve state is gepubliceerd. Beide pending-tickets zijn consumed (alleen attempted aanwezig). Dat bewijst laden, geen werkende routeguidance.
- Daarna op uptime 68 twee `0x5200 route-guidance request failed`; iAP2-log eindigt met `Device removed` en interface disabled. Geen verse video/CarPlay-ready-lease. Java meldt vervolgens stale guidance state (verwachte freshness-fallback bij verdwenen telefoonverbinding). Geen bewijs dat dit een nieuwe codefout is; niet als geslaagde routeproef presenteren. Gebruiker gevraagd of CarPlay zichtbaar is, en gemeld dat opnieuw verbinden nodig is. Niet automatisch confirmed schrijven; nieuwe routeproef is nog open.
- Gebruiker bevestigt daarna CarPlay zichtbaar. Hercontrole: mm-ipod heeft nieuwe PID 5218428 (eerste PID 2162810); `pidin -p mm-ipod mem | grep cw-rgi` leeg, terwijl iAP2 weer live verkeer toont. Concrete oorzaak: native proef-ticket was per PROCES verbruikt, USB-reconnect startte stock zonder preload. Deze proefbeveiliging was dus onvoldoende voor reconnecttests; niet verwarren met een parser-/guidancemappingfout.
- Hersteld en live: `unit/mm_ipod_rgi.sh` houdt een trial voor EEN PCM-BOOT via `/ramdisk/cw-guidance-native-trial` plus persist `attempted`. USB-herstarts laden daardoor dezelfde native proef; volgende volledige boot wist RAM en valt zonder confirmed terug naar OEM. Bevestigde modus ongewijzigd. Nieuwe wrapper SHA `1b5c95263ce61b96c96d269146a9ac85e4bd2bc3e7ad8f712eb346aaff522438`, originele wrapper `24ff9dcf94669d36978877c1265bd7b1c5f885ccf34b919fed43999efd0e43c3` bewaard als `guidance-before-reference-20261116/mm-ipod.wrapper` onder controls-root. Installatie `GUIDANCE_BOOT_TRIAL_READY`, exit0, QNX-syntaxcontrole geslaagd. Alleen starter aangepast; native/JAR-hashes blijven gelijk. Bestaande draaiende stockontvanger niet gekilld.
- Werkelijke Linux-shellfixture getest voor eerste start, reconnect, RAM-wis/rebootterugval en confirmed. Host Windows pytest: twee passed, een shelltest bewust skipped; dezelfde shellfunctie apart met stdlib-runner in Linux uitgevoerd en geslaagd. Gebruiker gevraagd in stilstand USB opnieuw te verbinden en route te starten. Na die actie logs/cwrG4 en Java apply controleren. Nog geen fysieke bevestiging en geen confirmed-markers schrijven.
- Snellere overdracht: RCC heeft werkende `gzip -dc`. JAR (75162 bytes) gecomprimeerd als 23153 bytes gestaged en op RCC naar `/net/mmx/ramdisk/...jar` uitgepakt; oorspronkelijke SHA daarna geverifieerd. Eerste ongecomprimeerde JAR-client afgebroken voordat installatie; geen permanente bestanden daardoor geraakt. Native payload 32238 bytes volledig geverifieerd. Vermijd opnieuw ongecomprimeerde grote JAR-overdracht wanneer gzip beschikbaar is.

- Gebruiker vroeg de volledige afhandeling te maken: stoppen, aankomst, herberekenen, appwissel en disconnect. Native `cw_rgi_consume_at`, `cw_rgi_tick` en `cw_rgi_end` maken de overgangen expliciet en deterministisch testbaar. Referentie `rgd_hook.c` gebruikt 800 ms grace voor gewone route_state=0, geen zero-timeout na REROUTING(5), en hard-clear bij disconnect/source_supports_rg=0. Die semantiek is overgenomen; nieuwe actieve data annuleert de pending reset en begint met schone routecaches.
- Native aankomst: expliciet iOS route_state=2 zet ARRIVED, verbergt lanes/actieafstand en wist resterende afstand/tijd; non-blocking 5s deadline volgens Fifthbro `destinationDisplayDuration=5000`. Herhaalde ARRIVED of aansluitende state=0 verlengt/verkort die periode niet. Na afloop geen heractivering door herhaalde late ARRIVED of gecachte payloads; nieuwe route_state=1 begint schoon. Nieuwe appbron annuleert de oude aankomstdeadline. Java toont een vooruitgestuurde arrival-manoeuvre niet als bereikt op 900m: Fifthbro parseAndApply hanteert laatste 70m of expliciet RS=2.
- In mm-ipod verzorgt een kleine lifecycle-worker deadline-expiratie zonder vervolgpacket. Mutex beschermt dezelfde state tegen receive/timer/Identify. Worker vernieuwt NOOIT de ontvangstlease: hard geterminerd proces of stilgevallen verbinding blijft onder de bestaande freshness-fallback vallen. Nieuwe Identify, afwijzing en unload publiceren een schone disconnect-state. SIGKILL/ontbrekend fysiek disconnect-event kan alleen via bestaande lease/read-grace worden ontdekt; geen onmiddellijke detectieclaim.
- Java-clear probeert ieder OEM-veld afzonderlijk; een mislukking houdt retry pending voor de volgende poll. Geen tweede Java-aankomsthold: dat kon stoppen/disconnect ten onrechte uitstellen. Originele huidige-positietekst wordt niet leeggeschreven; route-afstand, tijd, descriptor, lanes, GAL, rgActive en manoeuvrefase worden wel gereset.
- NIEUW wireformaat **CWRG4** (CWRG3 plus route_state/end_reason). Alleen nieuwe native + nieuwe guidance-JAR samen installeren. Java blijft CWRG1/2/3 lezen. Huidige lokale hashes: native `0a2cc0578270aa5f43405e011c8a60b1494b055963ddbaba0700886522f47042`; guidance-JAR `8b82136fdc41618f18579d5a6264aae1661ab36527e0c4ae3331b941d3d9b4f6`. Display/zoom-JARs ongewijzigd. Oude artifactclaims hieronder zijn historisch.
- Validatie: volledige native ASan/UBSan-suite incl. `tests/test_rgi_lifecycle.c` en 4536 mapper-oraclecases geslaagd; extra lifecyclefixture met appwissel geslaagd; Java/OEM/legacy-build en alle buildfixtures geslaagd, incl. aankomstafstand, expliciete RS=2, CWRG4 en foutinjectie/retry van clear; QNX-crossbuild en 10 gerichte Python-tests geslaagd. Geen unit/SD-installatie, commit of push gedaan. Fysieke proef blijft nodig voor daadwerkelijke telleracceptatie, aankomst en stop/herberekening op beide apps.

## Lokale guidancecorrectie 15 november — nog niet op de unit

### Volledige vervolgcontrole (nieuwste lokale status)

Lees `GUIDANCE_REFERENCE_AUDIT.md` voor bronrevisie, gecontroleerde keten,
protocol en de concrete fysieke test. Onderstaande eerste bullets beschrijven
de eerdere, kleinere correctie; dit vervolg vervangt die lokale status.

- Ook hersteld: cache met volledige uint16-manoeuvre-ID's (geen limiet op route-ID 63), behoud van gedeeltelijke updates, actuele afstandscursor, afzonderlijke lane-eventcache/selectie, signed hoeken naar BAP-richtingscodes en extra lane-richtingen. Vooruitgestuurde events wijzigen de actuele aanwijzing niet. Mapperuitvoer komt overeen met 4.536 vectoren uit de vastgezette referentie; fixture en herbouwtool staan in de repository.
- CWRG3 bevat type, staplengte, afstandsgeldigheid en cursor. Java gebruikt de bestaande OEM `updateBapManeuverState` voor Follow/Prepare/Action. Drempels en bargraph komen uit de referentie (1500/3000 m, maximaal 15% actiezone). Default verre aanwijzing blijft referentie Next; een pijl op 900 m is dus niet automatisch fout, maar is Prepare en geen Action. Geen zelfbedachte wachttijd tussen manoeuvres. Rijstroken blijven afhankelijk van expliciete iOS-zichtbaarheid.
- Huidige artifacts (lokaal, NIET live): native RGI `562f4b634a0dfe11bd738c9bd92ded175f84a234a0ba32fff658b3cc0d92e830`; guidance-JAR `a2155fb1630ecf635e3bf7e993f243bff7a3d7c009490fd7937547f1fc7b25b3`. Samen installeren: oude Java kent CWRG3 niet. Display- en zoom-JARs zijn inhoudelijk ongewijzigd. Niet naar unit/SD gedeployed, niet gecommit of gepusht.
- Geslaagd: volledige native suite met ASan/UBSan (inclusief bestaande display/video/listenertests), 4.536 referentievectoren, Java/legacy/notification/cluster/zoom/guidance-fixtures inclusief fase- en lanecontroles, volledige QNX-crossbuild en 10 gerichte Python-tests. Geen fysieke timing/positieclaim en geen volledige Python-suiteclaim. Volgende stap is gerichte fysieke guidanceproef met beide apps; kaartweergave en opstart niet wijzigen.
- Extra gebruikersinstructie: timing EN pijlpositie uit de referenties halen. Referentie `BAPBridge.sendManeuvers` heeft geen X/Y-velden; de eigen OpenGL-renderer heeft die wel (`maneuver_render/render.c`), maar bestuurt niet de originele Porsche-pijl. Geen renderer-pixeloffsets in BAP kopieren. Nieuwe regressie `test_app_independent_presentation` vergelijkt alle uitvoerstaat voor dezelfde Apple/Google-manoeuvre, afstand en lanes; alleen bronlabel mag verschillen. Zie de aparte sectie in `GUIDANCE_REFERENCE_AUDIT.md`. Productieartifacts ongewijzigd sinds bovenstaande hashes; geen nieuwe deployment.

- Gebruiker meldt fysiek snel wisselende manoeuvrepijlen op onjuiste momenten en nog steeds een verschoven manoeuvrepijl bij Apple Kaarten. Geen actuele unitlogs opgehaald; oorzaakpositie nog niet bewezen.
- Bevestigde codefout in `native/porsche_rgi.c`: 0x5201 TLV 0x0d is een reeks uint16-manoeuvre-ID's. Bij meerdere entries las onze code `be16(v+2)` (tweede entry) in plaats van de eerste. De oude C-test verwachtte dezelfde fout. Referentie lokaal `.tmp/mib2q-carplay-rgi`, origin `https://github.com/luka-dev/mib2q-carplay-rgi.git`, commit `21f501611b0b28dbdeb2849e8443ce90ec9517ff`: `hook/routeguidance/rgd_tlv.c` parseert iedere twee bytes als ID; `java_patch/com/luka/carplay/rgd/ManeuverPresentation.java` currentSlot gebruikt `maneuverOrder[0]`. `rgd_hook.c` bewaart prefetch en promoveert geen toekomstige entry wanneer de huidige nog ontbreekt.
- Lokaal gecorrigeerd: expliciete cursorselectie, eerste ID, 0x5202 alleen cache vullen (geen routeactivatie), ontbrekende actuele descriptor wist oude pijl en kiest geen toekomstige; lege lijst wist cursor, ontbrekende lijst behoudt cursor, oneven lijstlengte wordt voor mutatie geweigerd. Native log voegt cursor/selected toe. Nog bestaande beperking: directe manoeuvrecache-ID's 0..63, geen referentie-slotmapping voor hogere IDs; hogere actuele ID wist oude pijl maar kan geen descriptor tonen. Niet claimen dat de volledige referentieport gereed is.
- Bevestigde afwijking rijstrookzichtbaarheid: Java gebruikte `laneVisibility != 1`, dus onbekend=0 toonde reeds gecachte lanes. Referentie `BAPBridge.laneGuidanceVisible` vereist expliciet iOS showing=1. Onze wirewaarden zijn 0=onbekend,1=verborgen,2=zichtbaar; lokaal nu alleen `==2`. Dit kan verkeerde tellerindeling verklaren, maar fysieke pijlpositie nog niet bevestigd. Geen x/y-patch of eigen tijdschema toegevoegd. Nog aandachtspunt: lane-eventcache/cursor is niet volledig zoals referentie geport; huidige native parser bewaart laatste laneset.
- Validatie: native C-fixture met ASan/UBSan geslaagd (eerste/tweede entry, prefetch, ontbrekend huidig, lege/malformed lijst, geen heractivering gestopte route); 8 gerichte Python-tests geslaagd; volledige QNX-crossbuild geslaagd; Java-build/bytecodefixtures inclusief expliciete lanevisibility 0/1/2 geslaagd, plus bestaande notification/cluster/zoom-fixtures. Geen volledige Python-suite of fysieke test geclaimd.
- Nieuwe lokale artifacts: native RGI `34d2fa6658ffed185778524c3704e5a840988ed71d37e48a0abdcd68c9c45234`, guidance-JAR `8411e165c7c5db8ae461ce2604d38e5a45d517a56d9889d18c377ce13ea63fdf`. Andere gegenereerde split-JARs niet installeren: alleen guidance is gewijzigd. Niet gedeployed, niet gecommit/gepusht; live blijft de versie van 9 november. Volgende stap is gerichte replay/liveproef van actuele cursor + afstand, gevolgd door lane-eventselectie tegen dezelfde referentie; behoud kaart/zoom/startup.

## LIVE guidanceproef 9 november — actuele prioriteit, vervangt oudere gereedclaims

### Laatste vervolg: permanente activering en rijstrookfout

#### Nieuwste vervolg: permanente reconnect en appbron (9 november)

- Permanent geinstalleerd na toestemming: receiver `c020803207a59ac438e2ffe526110ffcb7294cac86236fcf1cb96da9eca3f847` en `/mnt/system/etc/eso/production/smartphone_integrator.json` `e042e65da4f366fef35c700528c7054fcf7f6e38dba23f7c291928895d91cb86`. Installatie `RECONNECT_PERMANENT_READY`, exit 0. Originele config hash `a1ac27b4f405346548e8e1bec82b1f5c3483dc73050d682ad4c9a80808f7cbc7`. Herstelkopie bij beide bestanden met suffix `.cw-before-reconnect-20261109`.
- Reconnectoorzaak in live logs: nieuwe OEM DIO-PID na USB-reconnect, oude supervisor stopte met `owner_alive=0`; RGI bleef doorlopen. Nieuwe `native/porsche_autosupervisor.inc` start de bestaande supervisor vanuit iedere nieuwe receiverinstantie, gebonden aan diens echte PID. Configgenerator `build-tools/prepare_reconnect_config.py` past uitsluitend CarPlay-child executable en env aan; OEM `dio_manager.cw-stock` krijgt capture-preload en constructoropt-in. Andere kinderen/config blijven behouden. Twee generatorregressietests slagen.
- Appbron: native RGI `791a8673bf198599fd261d6cdfd85f256bdc27537a072b045ee101e57e77d31e` permanent geinstalleerd (`GUIDANCE_SOURCE_READY`, exit 0), backup `cw-rgi.so.before-source-20261109`. Parseert iOS 0x5201 sourceName=0x13, sourceSupportsRouteGuidance=0x14, visibleInApp=0x0f volgens lokale referentie `.tmp/mib2q-carplay-rgi/hook/routeguidance/rgd_tlv.*`. Bij gewijzigde bron eerst oude manoeuvres/afstand/rijstroken wissen, daarna nieuwe deltas toepassen (ook als bron-TLV na afstand staat). Zelfde bron bewaart deltas. Unsupported bron deactiveert guidance. Geen eigen appkeuzelijst: iOS levert de geselecteerde bron. Nog geen bewijs dat alle apps dit correct melden.
- Identify wist ook native sessiecache. RGI-log toont nu bron, active, distance en epoch. Linux C-regressietest Apple 30m -> Google 900m en vervolgdeltas slaagt; QNX volledige crossbuild slaagt. Deze tests zijn geen fysieke bevestiging.
- Herstart aangevraagd om beide wijzigingen te laden; runtimebewijs hieronder bijwerken. SD/ZIP nog NIET bijgewerkt, werkboom NIET gecommit. Huidige Java blijft `fae18ec437ea7b479777859df649c28a8becfdc7b33b4cb2c7e1e385aaeeadbd`; confirmed-markers guidance en zoom behouden.
- QNX ksh accepteert `function name { ...; }`, niet `name()`. Gebruik nooit functienaam `hash`: bestaande alias `hash='alias -t'` overschrijft dat (installer unalias expliciet). Beide fouten zijn VOOR mutatie tegengehouden; uiteindelijke installatie exit0.
- Oudere bullets hieronder met andere native hashes, pending-status en 'nog NIET geladen' beschrijven eerdere mislukte fasen; bovenstaande status heeft voorrang.
- Runtime na eerste herstart bevestigd: `CARPLAY_ACTIVE display=1 context=70 size=800x480`; native `source=Google Maps active=1`, Java apply loopt door. Afstand bleef op die opname 0m: correcte afstand nog niet bewezen. Gebruiker meldt vervolgens 'het werkt'.
- Aanvullend permanente wrapper vervangen (beide `/mnt/app/eso/bin/apps/dio_manager` en controls `launcher.sh`), SHA `ff8e4ca38942597a1b94030d075a2c1614579ccc16673314558281c31136e178`. Bestaande opstart bleek ondanks configpatch nog shellwrapper te gebruiken. Wrapper doet nu `exec` OEM met `CW_PROCESS_SUPERVISOR=1`; constructor start begeleider, zonder oude parent/wait/restart-PID-keten. Script QNX-syntax gecontroleerd, `RECONNECT_LAUNCHER_READY`, exit0. Backups suffix `.before-reconnect-20261109`. Tweede herstart aangevraagd; aansluitend Telnet time-out, dus constructor-spawn na die laatste herstart NIET logmatig bevestigd. Oude shell-exit SD-logkopiepad bestaat niet meer; periodieke logborging/SD packaging nog nalopen.
- Nieuwste observatie gebruiker: MANOEUVREPIJL bij Google Maps gecentreerd, bij Apple Kaarten meer rechts (expliciet bevestigd). Java geeft geen x/y-positie voor guidancepijl; activeert lanes bij `laneVisibility != 1 && lanes.length != 0`. Hypothese OEM-layout door rijstrookbegeleiding; NIET bevestigd. Geen nieuwe lay-outpatch gedaan. Gebruiker test dit eerst en vraagt alle projectwijzigingen te committen; daarna voorlopig pauze.

- Gebruiker heeft expliciet permanente activering gevraagd. Beide confirmed-markers zijn geschreven en teruggelezen onder guidance-native en guidance-probe. Backups blijven aanwezig.
- Native actueel live: `e516dbe4339a842e7a0e9ae1e542bdc123d479dbfe91a44f5147a33df661a97d`. Ontvangstpoolregel gecorrigeerd naar AU37x `rc != 1`: alleen exact 1 draagt eigendom over. Andere positieve codes moeten ook terug naar pool. Eerder alleen rc<=0 gaf lekkage; geforceerd recyclen op message-ID kan ander eigendom beschadigen. Daarnaast heartbeat van cached route op ontvangen linktraffic (2 s), zodat de Java freshnesscontrole niet normale iOS-deltastilte als disconnect behandelt.
- Gebruiker bevestigde na Java setRgActive/setViewMode-correctie: “Dit werkt”, maar meldde daarna wegvallen. Laatste in deze fase live JAR was `e5a512581ca9c3599e469a8d6883f69f02c49ff9dca66d78e491cbb03729eef4`.
- NIEUWE concrete fout: bij vier lanes kwam CWRG2 direction=65491 binnen (=signed short -45 graden). Java lane-parser accepteerde alleen 0..255 en verwierp het hele guidancebericht, waarna clear. Laatste oude apply uptime147; native bleef doorlopen tot uptime283 met lanes. Lokale correctie staat in PorscheRouteGuidance.lane(): richting accepteert 0..65535 en wordt naar signed short gecast. Foutlogging toegevoegd (max iedere5s). Lege currentRoad wist OEM-huidige-positie niet meer; clear wist huidige straat ook niet meer.
- Nieuwe rijstrook-JAR `fae18ec437ea7b479777859df649c28a8becfdc7b33b4cb2c7e1e385aaeeadbd`: Java/legacy build en regressiefixtures met exact negatief lanevoorbeeld slagen. **Geinstalleerd en live hash teruggelezen**, via `.tmp/activate-guidance-lanes.sh`, RCC herstart. Beide confirmed-markers blijven actief. Eerste Java-log op uptime26 meldt nog geen native statefile (normaal voor mm-ipod-start rond44s). Fysieke bevestiging van deze laatste lane-fix ontbreekt nog.
- De overdrachthelper gebruikt nu 512-byte batches (2048 kon QNX input verliezen); geen reboot na mislukte activering (`GUIDANCE_TABLE_READY` is vereist). Eerdere mislukte RAM-overdracht heeft onbedoeld wel een herstart veroorzaakt; dit is in helper gecorrigeerd.
- Directe dmdt-query vereist `IPL_CONFIG_DIR=/etc/eso/production`; zonder dit crasht alleen de querytool (nieuwe dmdt-core), niet als PCM-crash interpreteren. Gebruik native/porsche_dm.c als juiste voorbeeld.

- Native RGI hoort in `mm-ipod`, niet in `dio_manager`. De AU37x-referentiebinary `librgd_hook.so` gebruikt schrijfbare `ident_info_funcs`/drivertabellen. Runtime textpatches werden op de Porsche geweigerd door `mprotect`.
- Exacte driver SHA256 `7b9a1a6beef7bc893bb5a824486f4ad5fc34912a0b894a6d24d171ab324a8cb7`. ELF RW-segment: file-offset = virtual address - 0x1000. `ident_info_funcs` VA 0xa9c40 (24 entries van 8 bytes). Lokale `iap2_drvr` VA 0xa9d00; ontvangstpointer op +0x20, NIET AU37x +0xe0. Dit is statisch en live geverifieerd.
- `native/porsche_rgi_hook.c` is nu een tabelhook. Laatste live hash `e1efe82bcee2cd907b3046bc9df662aef0e790af4ac13482d18d179b40677169`. Ontvangst volgt OEM transportcode met eigen inspectie. **NIET STABIEL: ontvangstpool raakt alsnog leeg na enige tijd; CarPlay valt uit.** Niet permanent bevestigen. Alleen drie 0x520x-types teruggeven aan pool was onvoldoende. Onderzoek packetownership en volledige referentiepipeline voordat opnieuw live laden.
- Fysiek/logmatig bewezen: Identify component toegevoegd, iOS `IdentificationAccepted`, 0x5200 verzonden, echte route-updates ontvangen en Java `apply` uitgevoerd. Waargenomen rotonde op 900 meter, manoeuvre 21/48, 2800 m resterend. **Geen pijlen fysiek gezien**; teller meldt routegeleiding inactief.
- Javafouten vastgesteld: `setGALState(true)` meldt alleen smartphone-navigatie en activeert GEEN RG-status. OEM `setRgActive(boolean)` bestaat en zet rgStatus. `setViewMode(1)` vertaalt naar rgType=0. `setCurrentStreet(turnTo)` veroorzaakte volgende straat in huidige-positieveld. Lokale Java-correctie voegt setViewMode(1), setRgActive(true/false) toe en gebruikt currentRoad; nog NIET geladen. Java-build en fixtures slagen. Nieuwe JAR SHA256 `e5a512581ca9c3599e469a8d6883f69f02c49ff9dca66d78e491cbb03729eef4`, alleen naar `/ramdisk/cw-guidance-display-fix.jar` gestaged.
- Huidige live launcher behoudt bevestigde zoom, laadt guidance via apart pending-ticket. Native wrapper `/mnt/app/armle/usr/sbin/mm-ipod` start echte OEM onder `connectwow-rgi/mm-ipod`. Zowel native als Java one-shot zijn attempted, niet confirmed; volgende proces/boot hoort terug te vallen. Controleer markers voordat herstart.
- Originele bestanden van deze sessie geborgd onder `/mnt/app/eso/hmi/connectwow-carplay/guidance-backup-20261109/`: mm-ipod, lsd.sh, dio_manager, launcher.sh, cw-rgi.so. De oude lsd.sh bevatte al een mislukte guidance-one-shot. De iAP2-config was reeds gepatcht met 520x-message-ID's, hash `5ca0a762dcf24bef3661f77dc4641433767026e4500a2a60f2c60ed0cc77af41`.
- Live logs `/ramdisk/cw-porsche-rgi.log`, `cw-porsche-rgi-java.log`, `cw-carplay-guidance.v1`, `/dev/shmem/iap2.log`. Laatste log: doorlopende updates tot uptime 737 s, daarna `No packets in receive list`, `Failed to send packet`, `Interface state disabled (2)`. Java clear na stale-state. Gebruiker meldt reset/CarPlay-uitval; behouden RAM-logs bewijzen geen volledige reboot.
- Overdracht: RCC mist `printf`, maar ksh `print -n '\\0ooo'` werkt. `.tmp/unit_console.py` is de sessiehelper voor read-only console en gechunkte staging. FTP poort21 reageerde niet; ftpd -D bracht geen listener op. Geen verdere tijd verspillen aan dezelfde mislukte methode.
- De eerdere 79-passed-suite en ZIP 854b37e1... horen bij de PRE-tablehook. Ze bewijzen de huidige native wijzigingen NIET. Oude tests/test_patch_iap2_config.py bevat nog verwachtingen voor verwijderde textpatches en moet inhoudelijk worden bijgewerkt. Huidig SD-pakket niet als gereed behandelen.
- Eerstvolgend: herstel/stabiliseer CarPlay zonder onbevestigde native hook, bewaar logs, toets packetpool-eigendom aan reference `transport_recv_pkt` en AU37x binary. Daarna Java-correctie apart fysiek testen. Geen gereedclaim op basis van alleen builds.

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


## Onderzoek oud Google-logo op originele satellietkaart

Zie `docs/SATELLITE_CLUSTER_LOGO.md`: exacte OEM-keten SatelliteMapsMediatorFSM
naar BAP MapView gevonden. Teller-overlay is aannemelijk, fysieke logo-only-
uitschakelproef nog niet gedaan. POI-logo_map.png niet als oplossing gebruiken.
Geen code of unit gewijzigd voor dit onderzoek.


## CarPlay-only satellietlogo-proef lokaal gebouwd (nog niet op unit)

Gebruiker verduidelijkte: alleen bij CarPlay moet het oude Google-logo weg;
op de originele satellietkaart mag de OEM-weergave terugkeren. Ge?soleerde
proef onder `optional/satellite-logo/`, builder `build-tools/build_satellite_logo_probe.py`.
E?n outgoing BAP-call wordt gefilterd, OEM opgeslagen mapView blijft intact.
Nieuwe helper pollt bestaande ready-lease500ms, herstelt laatste OEM-waarde bij
leaseverlies, opt-in JVM-property; geen constructor-thread, geen file-I/O in
BAP-callback. Geen guidance-/native-/startupwijzigingen. Boundarytest slaagt.
Hosttest: opt-in, suppress/restore, OEM-refresh, supplementary behoud en
retry bij fout geslaagd; ASM/legacy-bytecode en ongewijzigde andere zoomclasses
geverifieerd. Lokale bronzoomhash264f4231...6779a82; candidate
`build/PorscheCarPlayZoomLogo.probe.jar` hash
72a5feca56b0c2062d139cdfb906f028166fe7255a3d333e9e1af0c3f54a9e42.
Live bronzoomhash nog vergelijken v??r proefinstallatie! Effect MapView0 op
andere tellerfuncties onbewezen. NIET ge?pload/ge?nstalleerd, geen reboot.
Lees optional README voor exacte proefacceptatie. Niet als fysiek opgelost melden.


## Satellietlogo-proef ge?nstalleerd als one-boot proef; herstart aangevraagd

Gebruiker vroeg test en bevestigde stilstand/herstart. Live bronzoomhash
264f4231...6779a82 komt overeen met lokale bron. Nieuwe kandidaat heeft begrensde
RAM-transitielog (max64 regels), hash59842f9e68060680a93dcbb2eba6dbeb184dfd1295a626782b832c9905bcf542.
De eerdere hash72a5feca is hiermee vervallen.

`/ramdisk/cw-logo-probe-20261116/install.sh` gaf
SATELLITE_LOGO_ONESHOT_READY_NO_REBOOT. Nieuwe aparte JAR staat onder
zoom-probe/PorscheCarPlayZoomLogo.probe.jar. Originele zoom-JAR264f4231 blijft
ongewijzigd. LSD52e32b89ffee426b71c6836356ce684eaf102b884ebddbde066c05fc3e335f08
bevat uitsluitend optionele selectie van logo-JAR plus property binnen bestaande
zoom-enablebranch. Ticket satellite-logo-probe/pending wordt bij boot attempted;
volgende boot laadt weer gewone bevestigde zoom. Guidance/native/video niet gewijzigd.
Backup originele LSD93d7fed1102c20727a24acefbf43380001f5c9ef32319800bcbe74206d13e59e
in controls-v15/before-logo-probe-20261116/lsd.sh. Beide doelhashes teruggelezen.
Lokale fixtures voor lifecycle en one-shot slagen; scripts syntax op echte QNX goed.
Herstart via RCC mib2_ioc_flash uitgevoerd na expliciete bevestiging. Nu eerst
boot/CarPlay/kaart/guidance en /ramdisk/cw-satellite-logo.log controleren; fysiek
logo-effect nog niet bevestigd! Satellietstand voor de proef ingeschakeld laten.
Geen permanente logo-confirmatie en geen commit/push voor deze proef gedaan.


Logo-proef runtime na herstart: ticket attempted, J9 bevat logo-JAR en opt-in-property.
Nieuwe DIO2515065 gestart via video-bootstrap; supervisor2584699 en workers2961478/
2961538. Verse CWRD1 epoch466/timestamp80/800x480. Log
`/ramdisk/cw-satellite-logo.log`: `SATELLITE_LOGO view=0 extra=0 carplay=true`.
Dit bevestigt uitvoering/filtering, niet het fysieke verdwijnen van Google-logo.
Gebruikersvraag staat open: kaart zonder/met logo of geen kaart. Guidance meldde
op deze opname stale guidance state; route na herstart nog niet bevestigd. Geen
permanente activatie; bij volgende boot oorspronkelijke bevestigde zoom geselecteerd.


## Logo-proef fysiek bevestigd ? 16 november 2026

Gebruiker antwoordde expliciet `CarPlay-kaart zonder Google-logo` na bovenstaande
one-boot proef, met instructie satellietweergave ingeschakeld te houden. Het
onderdrukken tijdens CarPlay is daarmee fysiek bevestigd. Runtimebewijs:
`SATELLITE_LOGO view=0 extra=0 carplay=true`, verse kaartlease800x480.
Dit bevestigt niet automatisch OEM-logoherstel na disconnect, USB-reconnect,
zoom/guidance tijdens deze proef of koude boot. Die controles staan nog open.
Geen permanente logo-activatie gevraagd of uitgevoerd. Volgende boot selecteert
weer de oorspronkelijke bevestigde zoom-JAR; logo-proef-ticket is attempted.


## Aanvullend logo-onderzoek: definitieve BAP-wireketen

Zie `docs/SATELLITE_CLUSTER_LOGO.md`: AppConnectorNavi gebruikt functie44/0x2c,
MapViewAndOrientation_Status heeft expliciet STANDARD0/GOOGLE_EARTH1/TRAFFIC2.
Wirebericht bevat modus/status, geen bitmap/URI/logo-ID. Specifiek Google-logo
lijkt daarom een lokaal door de teller gekozen afbeelding; het exacte bitmapadres
is niet aangetoond en zou tellerfirmware/resources vereisen. Alleen PCM-firmware
is onderzocht. Geen nieuwe code/unitwijziging gedaan; permanente logo-onderdrukking
blijft ongewijzigd. Classhashes en bronnen in het onderzoeksdocument.


## Nieuw voorbereid: Porsche-routevoorrang, nog GEEN integratie/installatie

Gebruiker vroeg lokale voorbereiding van OEM-voorrang, automatische CarPlay-
terugkeer en een enkele tellerbron. Geen automatische iPhone-routestop beloofd.
Zie docs/NAVIGATION_PRIORITY.md voor exact firmwarebewijs, ontwerp, gevaren en
vervolgstappen. Pure policy in optional/navigation-priority/, getest tegen256
transitiecombinaties plus sessiewissel/arrival/unknown/stale-completion. Map, zoom,
guidance en logo krijgen dezelfde keuze. Geen threads/OEM-calls/I/O in de policy.
Actuele kerncode en boundary-fixture intact, geen unitverbinding of deployment.

Belangrijkste integratieprobleem: OEM-status via DSIResponseContainer.isRgActive,
niet via gedeelde CombiBAPListener.setRgActive; serialiseer eerst CarPlay-clear en
blokkeren VOOR OEM-publicatie. Bestaande async clear-retry mag OEM niet wissen.
Native supervisor moet bronkeuze ook volgen; Java-only contextwissel is niet genoeg.
Aankomsteindevent nog verifi?ren, geen willekeurige timer. De policy is nog geen
uitrolbare feature/JAR; geen fysieke test uitvoeren voordat adapters, race-tests,
legacy-J9-verificatie en herstelbare opt-in kandidaat gereed zijn. Niet gecommit.


## Review routevoorrang-voorbereiding

Op verzoek grondig gecontroleerd; nog steeds niet aangesloten/geïnstalleerd.
Policy hersteld: decision-identiteit (geen foreign/stale ack), kaart blijft staan
bij guidance-only transitie, ongeldige invoer kiest OEM, irrelevante telefoonupdates
verstoren OEM-transitie niet, expliciete eerste outputsynchronisatie nodig.
Uitgebreid naar2.304 overgangscombinaties en regressies; vier pytest-tests geslaagd
(policy, live-source/build-isolatie, guidanceboundary, logolifecycle).
Geen wijzigingen aan huidige Java/native/unit/build-tools voor deze voorbereiding.
Cruciaal integratiecontract: check/transitiewrites/ack onder dezelfde policy-monitor,
alle OEM-/CarPlay-writers aangesloten, clear vóór OEM-publicatie. Policy alleen
kan geen foutief uitgevoerde externe write terugdraaien. Zie laatste reviewsectie
in docs/NAVIGATION_PRIORITY.md. Niet als klaar voor fysieke installatie voorstellen.

## Actuele proef: navigatievoorrang, 17 november 2026

Deze sectie vervangt de eerdere status 'nog geen integratie/installatie'. De
opt-in kandidaat is gebouwd, lokaal getest en op de echte J9 gecontroleerd:
alle acht adapter/OEM-klassen LINK_PASS. De installer is daarna geslaagd.
Zie docs/NAVIGATION_PRIORITY.md en build/navigation-priority/manifest.json
voor ontwerp en exacte artifacthashes. Native kandidaat bevat de startupfix.

Eenmalige proef is met expliciete stilstandtoestemming herstart. Ticket is
attempted; RAM-marker cw-nav-priority.enabled aanwezig. Java meldt OEM_ENDING,
OEM_IDLE; CWNP1 permission met bron-PID1732710 is gepubliceerd. Native meldt
CARPLAY_ACTIVE display=1 context=70 size=800x480 t_ms=67570. Gebruiker bevestigt
CarPlay op PCM en CarPlay-kaart rechts zichtbaar. OEM-overname en terugkeer zijn
NOG NIET fysiek bevestigd: gevraagd originele Porsche-route te starten.
Niet permanent activeren voordat overname en terugkeer zijn bevestigd.

Installatiebackup: controls-v15/before-navigation-priority-20261116/ (historische
mapnaam). Native baseline 6e7fcdaa..., LSD baseline 5a7f5a08.... Volgende boot
zonder nieuw ticket valt terug op bevestigde losse Java-JARs; native opt-in is
zonder RAM-marker uit. Exact herstel via restore.sh uit build/navigation-priority.
Transfer via eenmalige RAM-helper TCP22110; .tmp/navigation-priority/transfer_current.py.
Gebruik geen telnet_push --binary: eerdere overdracht werd afgekapt en door hashes
geweigerd. Klein bootstrapbestand kan met .tmp/unit_console.py --upload.

J9-linkchecker vereist /ifs/lsd.jxe als bootclasspath (bevat ook JCL), expliciete
JAVA_HOME/LD_LIBRARY_PATH en absolute checker/JAR-paden. Relatieve uitvoering
vanuit installer gaf startupfout; absolute uitvoering slaagde. Geen bewijs van
werkelijk RAM-tekort. Offline ROM-audit vond een verweesde PorscheGeometry-call
in kandidaat ClusterService; uitsluitend die observer is verwijderd, originele
MapInterface-call behouden. Kandidaat-JAR fedd4e15..., native faf28f9c....

### Eerste OEM-overnameproef: fout gevonden, correctie nog niet geladen
Gebruiker startte OEM-route maar CarPlay bleef zichtbaar. Java logt OEM_ROUTE en
OEM_PUBLISHED; CWNP1 generation3 allow0, producer1732710. Native logt
CARPLAY_PRIORITY_RESTORE_OEM maar gs blijft context70; ack bleef generation2 allow1.
Live gs-query via dezelfde query-preload kost circa1s (ksh SECONDS). De proef had
slechts750ms voor query+switch+controle: onvoldoende. Builder hersteld naar het
bestaande gedeelde4s-budget. Nieuwe C-regressie simuleert1s per operatie en bewijst
herstel; native gate/freshness-test en QNX -Werror-build slagen.
Nieuw ELF SHA7dd4e09994a27f88a23d7b73f77d228d3f879e1d2220ad566f7bdd6708a89869
is atomair naar controls-v15/cw-window-candidate geplaatst; oude processen draaien
NOG. Java/JAR/LSD ongewijzigd. Backup blijft vorige baseline. RAM-update-script:
/ramdisk/cw-navigation-priority-20261117/update-native.sh. Vraag staat open om
alleen supervisor opnieuw te laden, zonder PCM-reboot. Actuele supervisor1810544,
receiver1732710, worker1958005 en renderer1958016. Controleer PIDs voor signalen.
Na toestemming SIGTERM supervisor, wacht op cleanup, start nieuwe --run met runtime
root /ramdisk/cw-link-probe-20261102 en actuele receiverPID. Geen processen blind
killen; log/applied/context moeten OEM-overname bewijzen. Fysieke bevestiging en
terugkeer na OEM-stop nog vereist; niets permanent bevestigen.

### Ontvangerverlies tijdens wachttijd op correctie
Gebruiker meldt CarPlay gecrasht en geeft toestemming nieuwe kaartproces te laden.
Read-only controle toont geen cw-window en geen dio_manager meer. HMI-J9 nog
actief. Receiver1732710 verloor bron; SI proces5419044 heeft -sm-restart1 en
-sm-time229393. Tweede receiver5484645: session-start-result status0 op238.012s,
map-control-session-forgotten op238.173s; supervisor stopt owner_alive0.
Geen bewezen crashoorzaak; niet stellen dat dit door querybudget komt. Nieuwe
ELF reeds geïnstalleerd, dus volgende receiverstart gebruikt correctie. Gebruiker
gevraagd USB opnieuw aan te sluiten met OEM-route actief. Nog geen tweede PCM-
herstart en geen blind handmatig receiverproces gestart (SI beheert die lifecycle).

### Correctie geladen na USB-reconnect
Nieuwe receiver6684782 en worker6815856 draaien; nieuwe supervisor startte na
USB-reconnect. OEM-route actief: CWNP1 gen6 allow0 producer6684782, CWNPA1 gen6
allow0 producer6684782 op357s. Live dmdt gs: display1 context72, alleen OEMlayer33.
Dit bevestigt juiste toestand bij starten met actieve OEM-route; nog GEEN bewijs
van actieve CarPlay->OEM-overgang onder gecorrigeerde ELF. Vraag om fysieke
Porschekaart+guidancebevestiging staat open. Daarna OEM-route stoppen en terugkeer
naar CarPlay verifiëren, daarna OEM-route opnieuw starten voor echte overgang.

### Terugkeer na OEM-stop fysiek bevestigd
Gebruiker bevestigt Porschekaart EN Porscheaanwijzingen zichtbaar; vervolgens
OEM-route gestopt en CarPlaykaart terug. Log bij controle: OEM_ENDING/OEM_IDLE,
CWNP1 gen13 timestamp535 allow1 producer6684782; CWNPA1 zelfde generatie/bron/allow.
Native meldt ACTIVE context70 op524818ms en eerdere PRIORITY_RESTORE_OEM-events.
Nog eenmaal expliciet gevraagd OEM-route te starten vanuit zichtbare CarPlaykaart,
zodat directe overname afzonderlijk fysiek wordt bevestigd. Proef blijft eenmalig;
geen permanente bevestiging of commit uitgevoerd. Ontvangercrash eerder nog niet
verklaard; geslaagde overgang is geen bewijs van volledige ruststartstabiliteit.

### Automatische CarPlay->Porsche-overname ook fysiek bevestigd
Gebruiker bevestigt expliciet 'Ja, Porsche neemt vanzelf over' bij starten van
originele route vanuit zichtbare CarPlaykaart. Runtime: CWNP1 gen14 timestamp586
allow0 producer6684782; CWNPA1 identieke generatie/tijd/allow/bron, native log
CARPLAY_PRIORITY_RESTORE_OEM. Beide richtingen nu fysiek bevestigd: OEM-route
start geeft Porschekaart+guidance; OEM-route stoppen geeft CarPlaykaart terug.
Niet permanent gemaakt: one-boot-ticket blijft attempted, geen confirmed-marker.
Eerdere SI/receiveruitval is nog niet verklaard en ruststart niet gevalideerd.

## Definitief actueel: permanente routevoorrang bevestigd, 17 november 2026
Gebruiker vroeg permanent activeren en commit. Uitgevoerd zonder PCM-herstart.
Launcher ondersteunt nu confirmed OF pending, met dezelfde native/JAR-hashguards.
Nieuwe live LSD SHA8b838ceec57c693a92d5ffd4774912d050adf1dca2b8232fc32b62d1c4833f1f.
Native SHA7dd4e09994a27f88a23d7b73f77d228d3f879e1d2220ad566f7bdd6708a89869;
JAR fedd4e15c80b9ae64f541c681502fdef18495e212c8e5097f657d153f6506995.
Confirmed-marker bevat 'physically verified both directions 2026-11-17'.
Eenmalige status uit eerdere secties is hiermee vervallen. Actuele Java-sessie
ongewijzigd; nieuwe launcher wordt volgende boot gebruikt. Meervoudige confirmed-
bootselectie en restore-markerwissen lokaal transactioneel getest.
Confirmatiegenerator: build-tools/build_navigation_priority_confirmation.py.
QNX-valkuilen tijdens activatie: functienaam hash botst met builtin (gebruik cw_hash),
printf ontbreekt (gebruik print). Eerste pogingen faalden veilig; rollback herstelde
launcher; laatste poging gaf NAVIGATION_PRIORITY_PERMANENT_CONFIRMED_NO_REBOOT.
De oorzaak van eerdere SI/receiveruitval blijft open; bevestigde omschakelingen
zijn geen bewijs voor alle ruststart-/reconnectscenario's. Niet opnieuw rebooten
zonder stilstandbevestiging. Geen push gevraagd. .tmp is niet onderdeel van commit.

### Unitopruiming na permanente activatie
Op gebruikersverzoek uitsluitend11 exacte tijdelijke bestanden verwijderd:
8 stagingbestanden in /ramdisk/cw-navigation-priority-20261117/ en3 cw-priority-
transfer-{0,2,4} bestanden in runtime. Geen transferhelperproces meer aanwezig.
Herstelscript vooraf persistent bewaard in /mnt/persist/connectwow-carplay/
navigation-priority/restore.sh; bron/doel SHA71a92fe58c0c270f550eac459eb4515e270d7993250b7e9c8b01ddecc8444731.
Actieve libs/JARs, alle herstelbackups en diagnostische logs behouden. Lege
RAM-stagingmap blijft staan (rmdir niet beschikbaar); verdwijnt bij reboot.
Runtime na opruimen: CWNP1/CWNPA1 gen18 timestamp864 allow1 producer6684782,
confirmed-marker behouden. Geen herstart uitgevoerd.

## Backups op unit verwijderd op expliciet verzoek
Na 'backups moeten ook weg' oude kopieën verwijderd:30 genoemde losse historische
bestanden in controls-v15,9 before/guidance-before submappen, root/backup en
root/guidance-backup-20261109, persist/navigation-priority/lsd-before-confirm.sh en
restore.sh. Actieve launcher eerst aangepast om voor hashcontroles het actieve
cw-window-candidate te gebruiken in plaats van before-navigation-priority. Beide
confirmed boots en fallback/restore transactiontest slagen. Nieuwe permanente LSD
SHA3d7e05b5c91a8448f0d91ad036465bbd78b1a29d561a7a75520cd46fb6152af2.
Confirmed-marker behouden; native/JAR/capture ongewijzigd, geen reboot.
De eerdere herstelpaden naar before-* bestaan op de unit NIET MEER. Gebruik voor
herstel lokale/repository-artifacts of OEM firmware, niet het oude restore.sh.
Stockbestanden buiten ConnectWow-map zijn geen verwijderbare testbackups:
dio_manager.cw-stock wordt daadwerkelijk uitgevoerd door CarPlay; lsd.sh.cw-stock
is het bestaande OEM-pad voor profielwrappers. Die runtimebestanden behouden.
Alleen RAM-stagingbestanden opnieuw verwijderd; diagnostische logs blijven staan.
Wijzigingen aan package/confirmation-builder hiervoor nog niet gecommit.

## Overdraagbaar SD-pakket voor tweede unit, 17 november 2026
Gebruiker wil de schone installatie ook op andere navigatie kunnen gebruiken.
Compleet nieuw overlaypakket gebouwd, GEEN installatie op verbonden auto uitgevoerd.
Scope uitsluitend schone unit met exact MU1417/OEM-/displayprofiel; bestaande
ConnectWow/CarPlay-modificaties worden bewust geweigerd voor schrijven. Andere
firmware/PCM/Audi vereist een apart onderzocht profiel. Online Menu en originele
CarPlay moeten al functioneren. Zie docs/PORTABLE_INSTALL.md voor gebruikersstappen.

Artifact: build/porsche-carplay-MU1417-portable.zip (circa164kB), SHA
1e7eda3b555df4e9d95f86fa53c58c308727e06cec34f16fbcc5adb74a01f386.
Builder build-tools/build_portable_sd.py --efs-root <originele efs-system root>.
Hier gebruikt: backend-private/.tmp/porsche-carplay-mu1417/native-analysis/efs-network.
Pinned bestaande, fysiek gebruikte ELF/libraries/JAR onder verified/mu1417-20261117/;
manifest bevat exacte hashes en scope. De oude capturebron is NIET herbouwd:
c0208032... is read-only van de unit uitgelezen en op SHA geverifieerd. Tijdelijke
RAM-uitleeshelper na afloop verwijderd. Geen geheimen/auto-identiteit gekopieerd.

Nieuwe templates unit/portable_install.sh, portable_hmi.sh, portable_link_check.sh.
Menu: check, install, confirm, restore, reboot, logs, status. Kort onderscheiden
scriptnamen voorkomen eerdere Online Menu-updatealiasing. Pakket is een overlay,
geen volledige SD/firmware of CarPlay-activering. HMI-wrapper zet alleen bewezen
opties en exec't eigen originele doelunit-HMI; geen gekopieerde testunit-LSD/VIN.
Installatie maakt minimale benodigde OEM-runtimepaden, bewaart herstelkopieën van
de doelunit op SD online/cw-release/recovery, geen stapel proefbackups op unit.
SI krijgt uitsluitend geteste cw-carplay-start exec; iAP2 uitsluitend geteste ident-
registratie. Eerste volledige boot is proef. Zonder bevestiging volgende boot OEM-
HMI; bevestigingsactie na fysieke proef nodig. Geen impliciete reboot: aparte knop.

Controles: exacte OEM DIO/LSD/mm-ipod/SI/iAP2/display hashes vóór writable mount,
complete payloadmanifest, echte J9-linkcheck vóór installeren, hashcontrole staging,
atomische filevervanging, rollback en read-only remount. Onvolledige rollback geeft
expliciete fout en behoudt artifacts/herstelmap. Herstel kan met beschadigde native
library (onafhankelijke verifier op SD). Geen garantie bij harde stroomonderbreking;
SD-herstelmap behouden. Geen oude live installer op huidige opgeruimde unit draaien.

Verificatie: tests/portable_install_transaction.py met echte legacy QNX-ksh in
qnx65-armv7:4.9:11 scenario's PASS (wrong OEM, corrupte payload, mount, rename,
late rename, copy, mislukte rollbackmelding, proefbootfallback, herhaald confirmed,
mislukt restore met rollback, corrupt installed library herstellen). OEM-inhoud,
mounts en J9 in deze fixture gesimuleerd; geen GPU/iPhone/tweede fysieke unit.
Tests/test_portable_package.py:3 PASS (determinisme/geen testunitafhankelijkheid,
verkeerde OEM weigeren, gemuteerde verified binary weigeren). Alle12 ZIP-scripts
slagen in QNX-ksh -n, LF gecontroleerd. Bestaande receiveruitval/ruststart blijft
open; nieuwe verse installatie nog NIET fysiek getest op tweede navigatie.
Bronnen/documentatie en wijzigingen na17ab41b nog niet gecommit/gepusht.

### Vastlegging portable pakket
Op gebruikersverzoek worden de opschoning, backupvrije launcherafhankelijkheid,
portable installer/builder, pinned release-artifacts, documentatie en tests samen
gecommit. Laatste controle:3 pakkettests en11 QNX-ksh-transactiescenario's geslaagd.
Tijdelijke .tmp-bestanden en gegenereerde build-ZIP vallen buiten deze commit.
De ZIP is reproduceerbaar met de gedocumenteerde originele efs-configuratie.
Deze actie bevat geen nieuwe unitinstallatie en geen Git-push.
