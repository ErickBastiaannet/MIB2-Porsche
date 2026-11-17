## Actuele status ? 17 november 2026

Op MU1417 fysiek bevestigd: een originele Porsche-route neemt kaart en guidance
over vanuit actieve CarPlay; stoppen van die route brengt de CarPlay-kaart terug.
De gebruiker heeft permanente activatie gevraagd; deze is op de unit bevestigd.
De launcher controleert de native/JAR-hashes bij elke boot en gebruikt dezelfde
bronkeuze voor kaart, guidance, zoom en logo. Zonder Porsche-route blijft de
CarPlay-kaart ook zonder telefoonroute beschikbaar. Telefoonroutes worden niet
be?indigd. Ruststart en de oorzaak van een eerdere SI/receiveruitval zijn nog
niet volledig gevalideerd. Onderstaande ontwerp-/voorbereidingsnotities zijn
historisch waar zij zeggen dat installatie nog niet heeft plaatsgevonden.

Build: eerst de kandidaat en ROM-audit bouwen, daarna
`python build-tools/build_navigation_priority_package.py`. Het pakket installeert
bewust eerst een eenmalige proef. Alleen na fysieke bevestiging genereert
`python build-tools/build_navigation_priority_confirmation.py` de gehashte
`build/navigation-priority/confirm.sh` voor het bestaande testinstallatiepad.
De confirmatie vraagt geen reboot en behoudt de baselinebackup; `restore.sh`
verwijdert ook de permanente bevestiging en herstelt de vorige bestanden.
Exacte actuele unitstatus en resterende controles: `docs/CODEX_HANDOVER.md`.

# Porsche-route krijgt voorrang op CarPlay

## Laatste offline controle - 17 november 2026

De kandidaat is bijgewerkt voor de huidige startupfix6e7fcdaa. De ROM-audit
controleert1320 memberverwijzingen uit22 Java1.2-klassen: geen ontbrekende,
onbevestigde of ongeldige private verwijzingen. Een oude onbeschermde aanroep
naar niet-meegeleverde PorscheGeometry is alleen in de kandidaat verwijderd;
de originele showKombiMap-aanroep blijft behouden. Geen Java-geometryworker toegevoegd.
Packagebuilder vereist de audit voor exact dezelfde JAR; rapport zit in ZIP.
Zie build-tools/verify_priority_rom_links.py en CODEX_HANDOVER.md voor hashes.

Nog NIET op auto geactiveerd: aparte J9-proef op unit stopte met VM-start/OOM
voor mount/schrijven. De controleomgeving is lokaal aangepast naar historisch
librarypad en absolute prefix; nog niet op QNX opnieuw uitgevoerd. Offline
API/bytecodebewijs is geen vervanging voor die VM- en fysieke eenmalige proef.


Status op 17 november 2026: afzonderlijke Java/native testkandidaat gebouwd.
Pakket: `build/porsche-navigation-priority-MU1417-test.zip`.
Niet op de auto geladen of fysiek bevestigd. De bestaande baseline-broncode,
bevestigde artifacts en live installatie zijn ongewijzigd.

## Actuele testkandidaat

De oorspronkelijke beleidsmodule is nu aangevuld met afzonderlijke adapters:

- `NavigationPriorityRuntime.java` onder optional/navigation-priority. Geldige
  DSINavigationDispatcher.updateRgActive(boolean,int)-events trekken eerst de
  CarPlay-toestemming in en ruimen uitsluitend eigen guidance op. Daarna laat
  de originele dispatcher de melding verwerken. ClusterService.updateRgActive
  geeft bij de RETURN van een inactive-event de OEM-routekeuze weer vrij.
  Herhaalde inactive-events resetten geen lopende CarPlay-route.
- De bestaande guidance-poll publiceert de keuze; er wordt geen nieuwe worker
  vanuit een constructor of extra timerthread gestart.
- Guidance apply/clear wordt in de kandidaat bewaakt. OEM BAP-writers krijgen
  tickets; een CarPlay-batch wacht op lopende OEM-writes. Geen OEM-monitor wordt
  vastgehouden terwijl een nieuwe ticket wordt gevraagd. De twaalf bewaakte/
  synchronized BAP-methodes eindigen hun ticket ook bij uitzonderingen.
- Na OEM-overname zijn oude CarPlay-clear-retries geblokkeerd. Bij terugkeer
  wordt de bestaande guidancecache voor een volledige replay ongeldig gemaakt.
- De gekopieerde PorscheCluster-readycontrole gebruikt dezelfde autoriteit.
  Daardoor volgen zoom en de bestaande logo-helper dezelfde keuze. De Java-
  zoomqueue wordt bij overname geleegd; een al verstuurde iOS-opdracht kan niet
  worden teruggenomen. De bestaande capturebibliotheek is niet vervangen.
- Native generatie van porsche_unit.c gebeurt uitsluitend in build/navigation-
  priority. De opt-in RAM-marker activeert de nieuwe gate; zonder die marker
  blijft de baselinekeuze actief. De decoder blijft bij OEM-voorrang ontvangen.
  Beide CarPlay-activatiepaden lezen de actuele toestemming opnieuw voordat ze
  context70 overnemen. OEM-herstel heeft een gedeeld budget van4000ms (gelijk aan het bestaande omschakelpad; een live query duurde al circa1s) en wordt
  na een mislukking opnieuw geprobeerd. De acknowledgement komt pas na een
  waargenomen contextwisseling; de UI-readylease wordt pas na activering gezet.
- `CWNP1`: generation/timestamp/allow/producer met CRC en3s-freshness. Een
  ontbrekend, corrupt, te oud, toekomstig of verkeerd-sessie-record blokkeert
  CarPlay in opt-in mode. `CWNPA1` bevestigt de native uitvoer. Java accepteert
  alleen een geldige UI-lease plus native bevestiging van dezelfde bron-PID.

### Builders en artifactgrenzen

- build-tools/BuildNavigationPriority.java: exacte afzonderlijke bytecodepatches.
- build-tools/build_navigation_priority_candidate.py: hash-pint de bevestigde
  logo/zoom- en guidance-JARs en de originele dispatcherklasse; bouwt een nieuwe
  gecombineerde JAR. De oude losse JARs worden niet overschreven.
- build-tools/prepare_navigation_priority_native.py en
  build-tools/build_navigation_priority_qnx.sh: genereren/bouwen alleen de nieuwe
  native kandidaat. De boundary-fixture blijft intact.
- build-tools/build_navigation_priority_package.py: eenmalige starter, install,
  restore, verplichte link-check, manifest en LEESMIJ. Controleert exact de
  bestaande kaart6e7fcdaa (inclusief startupfix) en starter5a7f5a08 voordat iets wordt geschreven.
- Originele dispatcherklasse: b2857648820390ddd238f1ce1e550b62203cff834aaa08375b561b588e144063.

De gecombineerde kandidaat wordt als ENIGE bootclasspath-prefix geselecteerd
in de proefboot; de bestaande guidance-prefix wordt die boot niet dubbel geladen.
Bij de volgende HMI-start zonder nieuw ticket worden de bevestigde losse JARs
weer gekozen en de RAM-marker verwijderd. De native kandidaat staat dan nog op
app maar de prioriteitsfunctie is uitgeschakeld. restore.sh zet de exacte vorige
native binary en lsd-starter terug; daarna herstarten.

### Uitgevoerde controles

-2.304 policytransities plus initiÃ«le synchronisatie, tokenidentiteit,
 guidance-only kaartbehoud, ongeldige invoer en sessiewissels.
-Hosttest van de werkelijke runtime-adapter met echte CRC-records, verlopen/
 verkeerde-sessiegegevens en gelijktijdige OEM-/CarPlay-writers. Gecontroleerd:
 een lopende OEM-write kan afronden, CP wacht, een nieuwe OEM-route onderbreekt
 na de CP-batch en een late CarPlay-clear wordt vervolgens geweigerd.
-ASM-stackcontrole van alle gewijzigde methoden en legacyklasseversies.
-De bestaande RouteGuidanceTextFixture slaagt ook tegen de gewrapte guidance
 met de optie uitgeschakeld (afzonderlijke host-JVM met -Xverify:all).
-QNX6.5 ARM-build geslaagd, -Wall -Wextra -Werror.
-Host-C-test van de echte wire/gatefunctie: CRC, bronbinding, deadlines,
 opt-out-baseline en fail-closed ongeldige input.
-Ksh-test van het echte pakket op mockfilesystem: corrupt bestand weigeren
 vÃ³Ã³r mount, herstel bij tussentijdse renamefout, juiste ene prefix in de
 proefboot, volgende-boot-terugval, native/lsd-herstel en read-only-remount.
-Bestaande guidance-boundary en logo-lifecycle blijven slagen.

### Grenzen van dit bewijs

Geen fysieke routewissel of J9-linkcontrole op de auto uitgevoerd. De installer
vereist de aparte side-effectvrije J9-linkcontrole vÃ³Ã³r schrijven, met32MB heap
en een20s-time-out. Dit is geen vervanging voor de zichtbare proef.

Aankomst wordt in deze eerste kandidaat vrijgegeven nadat de originele
inactive-update door ClusterService is verwerkt. Een afzonderlijke duur of
voltooiingscallback van de aankomstpresentatie is nog NIET bewezen; de eerdere
abstracte OEM_ARRIVAL-hold is daarom geen automatisch gedetecteerde functie.
Dit moet in de fysieke aankomstproef worden beoordeeld, zonder willekeurige timer.
Er is geen stopcommando naar iPhone-apps en geen audio-overname toegevoegd.
Zie optional/navigation-priority/LEESMIJ-TEST.txt voor de afgesproken proef.

## Oorspronkelijke voorbereiding en ontwerpcontrole

De paragrafen hieronder beschrijven de eerste beleidsmodule en de destijds
open integratiepunten. De actuele implementatie en resterende grenzen staan
hierboven; niet de historische tekst als actuele installatiestatus lezen.

## Afgesproken gedrag

| Originele route/presentatie | Geldig CarPlay-beeld | Kaart en bediening | Guidance |
| --- | --- | --- | --- |
| Route actief | Ongeacht | Porsche | Porsche |
| Originele aankomstpresentatie nog bezig | Ongeacht | Porsche | Porsche |
| Status nog onbekend | Ongeacht | Porsche | OEM ongemoeid |
| Geen originele route/presentatie | Ja, bekende videosessie | CarPlay | Verse CarPlay-route indien beschikbaar |
| Geen originele route/presentatie | Nee | Porsche | OEM ongemoeid |

Kaart, pijlen, afstand, straat-/bestemmingstekst, zoomdoorgifte en de bestaande
CarPlay-logo-onderdrukking moeten dezelfde bronkeuze volgen. Geen willekeurige
kaart-/telefoonpagina wisselen: de keuze betreft alleen de tellerkaart.
Geen iPhone-route stoppen, geen app afsluiten, geen CarPlay-audio onderdrukken.
Dubbele gesproken instructies vallen buiten deze eerste implementatie.

## Bevestigde firmware-ingangen

- `NavigationEnv.getContainer()` levert `DSIResponseContainer`.
- `DSIResponseContainer.isRgActive()` en `setRgActive(boolean)` zijn synchronized
  en lezen/schrijven de originele `rgActive`-waarde. Ook `isRgStopped()` en
  `getNavstateOfOperation()` bestaan; hun aanvullende statussemantiek moet nog
  in de oorspronkelijke callgraph worden gevolgd.
- `ClusterService.refreshRGIValid()` gebruikt zelf container.isRgActive().
- `ClusterService.updateRgActive(boolean)` stuurt OEM-modellen, clusterViewMode,
  clusterKDKHandler en CombiBAPListener aan. Dit is niet hetzelfde als de
  CarPlay-helper die direct `CombiBAPListener.setRgActive(true)` aanroept.
- `NaviAppHandler.updateRgActive(boolean)` bewaart routeGuidanceRunning;
  responseStartRouteGuidance/responseStopRouteGuidance bestaan, maar worden
  voor deze opdracht NIET als automatische iPhone-stopfunctie aangesloten.

Exact teruggewonnen DSIResponseContainer.class SHA-256:
9aefbe9ad56f9141d125ba59d661d3b54486f881939c557c070c715ba4beabd6.
Analyse: .tmp/navigation-priority/oem-route-state.jar en javap-output.
De standaardwaarde false bij opstart is niet automatisch een ontvangen/valide
OEM-idle-event. De adapter moet initialisatie/bronbeschikbaarheid aantonen.

## Voorbereide module

`optional/navigation-priority/org/connectwow/carplay/PorscheNavigationPriority.java`
is een zuivere policy zonder I/O, threads, OEM-aanroepen of installatiestappen.

- Inputs: OEM_UNKNOWN/IDLE/ROUTE/ARRIVAL, gevalideerde videobeschikbaarheid,
  verse routegegevens en positieve telefoon/videosessie-ID.
- Output: gewenste kaart-/guidancebron en overgangsacties. Die acties zijn
  interne ontwerpbeslissingen, GEEN verzonnen Porsche/CarPlay-API-methodes.
- Alleen oorspronkelijke idle en geldig beeld met bekende sessie geven CarPlay
  voorrang. Onbekende status, route en aankomst blijven OEM.
- Nieuwe Porsche-route blokkeert CarPlay-uitvoer direct in de policy, ook als
  de fysieke omschakeling nog moet worden uitgevoerd.
- Transities worden pas bevestigd met acknowledge na succesvolle uitvoering.
  Een verouderde of uit een andere module afkomstige beslissing kan niet bevestigen;
  de bevestiging vereist de identiteit van het actuele decision-object.
- Nieuwe telefoonsessie forceert oude CarPlay-uitvoer weg en volledige replay;
  oude begeleiding mag niet in de nieuwe sessie terugkomen.
- Ongewijzigde input veroorzaakt geen nieuwe omschakelactie. Geen debounce,
  vaste aankomsttimer of afgeleide route-afstand als activiteitsdetectie.

Hosttests (`tests/test_navigation_priority_policy.py`) controleren 2.304
transitiecombinaties plus aankomstvasthouden, directe OEM-preemptie,
verouderde completion, sessiewissel, onbekende sessie, map-only en zoom/logo-gates.
Aanvullend getest: vreemde tokens met hetzelfde volgnummer, initiÃ«le synchronisatie,
ongeldige invoer vanaf actieve CarPlay, geen kaartuitval bij alleen guidanceverlies,
geen uitstel van OEM-overname door gewijzigde telefoonstatus, en build-isolatie.
Ze draaien met javac --release8 en host-JVM -Xverify:all. Nog geen legacy-J9-
bytecodeconversie of fysieke validatie van deze nieuwe module uitgevoerd.

## Aansluiting die nog moet worden gebouwd

1. Volg eerst het oorspronkelijke DSI-eventpad tot setRgActive en de fan-out
   naar OEM-guidance. Bevestig de exacte aankomst-/eindpresentatiecallback;
   geen zelfgekozen timeout en niet alvast aannemen dat rgActive=false die
   presentatie volledig heeft afgesloten.
2. Sluit de autoriteit aan VOOR de OEM-guidance-publicatie. Gebruik een gedeelde
   serialisatiegrens voor CarPlay apply/clear, overgang en OEM-publicatie.
   Een vooraf los gecontroleerde boolean is niet genoeg om races te voorkomen.
   Gebruik dezelfde monitor als de policy (`synchronized(policy)`) voor de
   controle isCurrentTransition, side effects en acknowledge. Alle relevante
   OEM-/CarPlay-writers moeten daaraan meedoen. Een losse acknowledge achteraf
   kan reeds uitgevoerde foutieve writes niet ongedaan maken.
3. Stop bij OEM-overname eerst CarPlay-publicaties en pending clears. Wis nog
   getoonde CarPlay-routevelden VOOR OEM-aanwijzingen worden gepubliceerd.
   De bestaande PorscheRouteGuidance.clear() mag na die overname NIET alsnog
   setRgActive(false), lege pijlen of lege bestemmingsgegevens publiceren.
   currentStreet/actuele positie niet als routeveld generiek wissen.
4. Laat native renderer EN Java-contextrouter dezelfde bronkeuze respecteren.
   Alleen Java selectContext aanpassen is onvoldoende: de native supervisor
   kan context70 opnieuw activeren. Onderdruk geen frames door de sessie te
   vernietigen; behoud waar mogelijk CarPlay-ontvangst voor snelle terugkeer.
   Een eventueel nieuw Java/native-statusbestand moet versie, CRC, freshness,
   generation en duidelijke unknown/fallbacksemantiek krijgen en apart getest.
5. Laat zoominvoer en reeds gequeued zoomcommando's dezelfde bron volgen.
   PorscheClusterControls gebruikt nu alleen de ready-lease; die is na een
   keuze voor OEM niet voldoende. Controleer de native dequeue-kant ook.
6. Laat de logo-optie effectieve CarPlay-weergave volgen, niet alleen aanwezige
   CarPlay-pixels. Anders kan het originele satellietlogo onbedoeld ontbreken.
7. Bij vrijgave door OEM: bevestig einde aankomstpresentatie, accepteer alleen
   verse CarPlay-routecache van de huidige sessie, forceer volledige replay
   en voorkom dat OEM-restvelden na de CarPlay-overname terugkomen.
8. Bouw een opt-in kandidaat met volledige bron-/payloadhashes, legacy-J9-
   verificatie en eenmalige herstelbare proef. Bewaar de huidige bevestigde
   video-starter, kaart-, zoom/logo- en guidancebestanden als herstelbasis.

Geen van deze integratiepunten is door alleen de policytest bewezen opgelost.
De bestaande boundary-fixture blijft ongewijzigd; deze beschermt de huidige
werkende broncode tijdens deze voorbereidende fase.

## Latere fysieke acceptatie

- Zonder Porsche-route: huidige CarPlay-kaart/guidance/zoom blijven werken.
- Start Porsche-route terwijl CarPlay-route loopt: direct OEM-kaart en alleen
  OEM-velden, juiste zoom, geen opflitsende CarPlay-pijlen of logo-aanpassing.
- Herberekenen en een nieuwe Porsche-route houden OEM-voorrang.
- Stop/arriveer: originele eindpresentatie afronden, dan geldig CarPlay-beeld
  terug; zonder geldig beeld OEM laten staan.
- USB los/vast tijdens Porsche-route verandert niets aan de OEM-voorrang.
- Slapen/herstarten en onbekende status geven geen onbedoelde CarPlay-overname.

Testcommando (JDK via JAVA_HOME of PATH):
`python -m pytest tests/test_navigation_priority_policy.py tests/test_guidance_processing_boundary.py -q`


## Review van de voorbereiding

Controle op 16 november 2026, geen autoverbinding of runtimewijziging:

- Bevestiging alleen op generation was te zwak: een beslissing van een andere
  instantie kon hetzelfde nummer hebben. Hersteld met objectidentiteit; getest.
- Guidance-only wijziging blokkeerde ook kaart/zoom/logo tijdens de transitie.
  Hersteld: bestaande geldige kaart blijft bij dezelfde videosessie beschikbaar;
  guidance zelf blijft geblokkeerd tot veilige bevestiging. Getest.
- Onjuiste status/session-input liet eerder bij een exception de vorige keuze
  staan. Nu fail closed naar OEM_UNKNOWN; getest vanaf actieve CarPlay.
- Onverwante telefoonupdates tijdens OEM-overname konden transities onnodig
  verouderen. De token verandert nu alleen bij een andere effectieve beslissing
  of een voor CarPlay relevante sessiewissel. Getest.
- Bij opstart werd impliciet aangenomen dat de uitvoer al Porsche was. Nu
  vereist de eerste beslissing expliciete synchronisatie met de fysieke uitvoer.
  De adapter mag bij onbekend huidig guidance-eigendom niet blind alle velden
  wissen; originele Porsche-output moet intact blijven. Getest op policy-niveau.

Vier pytest-tests geslaagd: uitgebreide policyfixture, runtime/build-isolatie,
bestaande guidance-boundary en bestaande logo-lifecycle. Geen regressietests
nodig voor ongewijzigde native code; native integratie is juist nog niet aanwezig.

De resterende risico's zijn niet door de policy verholpen: externe writers die
het gedeelde slot niet gebruiken, een renderer die toch context70 terugpakt,
aankomst-eindsemantiek, validatie van verse routes per telefoonsessie en de
legacy-J9-/fysieke proef. Daarom nog geen uitrolbare of volledig bewezen feature.


## Reproduceerbare bouwvolgorde voor deze kandidaat

Vanuit de repositoryroot, met de bestaande OEM-buildinputs en de bevestigde
build/lsd-logo-confirmed.sh:

1. `python build-tools/build_navigation_priority_candidate.py --jdk <jdk-bin> --dispatcher-jar <teruggewonnen-dispatcher.jar>`
2. `python build-tools/prepare_navigation_priority_native.py`
3. `docker run --rm --entrypoint /bin/sh -v "${PWD}:/src" -w /src qnx65-armv7:4.9 build-tools/build_navigation_priority_qnx.sh /src`
4. `python build-tools/build_navigation_priority_package.py`

De dispatcher is lokaal teruggewonnen onder .tmp/navigation-priority/dispatcher.jar;
classhash wordt door de builder gecontroleerd. Dit is een OEM-buildinput, niet
iets om als zelfgemaakte stub in de unit te laden. De compile-only stubs worden
niet in het uitrolpakket opgenomen. RuntimeLinkProbe is wel expliciet onderdeel
van de kandidaat-JAR voor de aparte, side-effectvrije J9-preflight.

Pakkettransactietest in de toolchain:
`docker run --rm --entrypoint /bin/sh -v "${PWD}:/src" -w /src qnx65-armv7:4.9 -c 'PATH=/usr/bin:/bin python3 tests/navigation_priority_transaction.py'`
De echte J9 wordt uitsluitend in die mockfilesystemtest vervangen door een mock;
install.sh op de auto voert de echte linkcontrole verplicht uit.
