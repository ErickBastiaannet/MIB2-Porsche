# Guidance-portmatrix — Porsche MU1417

**Vervolg op deze audit:** de gebruiker beperkte de wijziging expliciet tot de verwerking binnen de bestaande werkende guidanceketen. Die zeven verwerkingsstappen zijn daarna lokaal uitgevoerd; zie [GUIDANCE_CHECKLIST_PROGRESS.md](GUIDANCE_CHECKLIST_PROGRESS.md) voor actuele status, tests en CWRG5-kandidaat. Onderstaande tabel blijft de oorspronkelijke auditstand; lees haar niet als status van de nieuwere kandidaat. Ontvangsthook, kaart en starters zijn bij dit vervolg ongewijzigd gebleven.

Gecontroleerd op 16 november 2026. Dit is een broncode-audit van de **lokale kandidaat**, niet een verklaring over de nu draaiende software op de auto. Tijdens deze audit is geen broncode, pakket of unit gewijzigd; alleen documentatie is bijgewerkt. Er zijn voor deze audit geen nieuwe tests gedraaid.

## Afbakening en bronnen

Primaire referentie: `luka-dev/mib2q-carplay-rgi`, commit `21f501611b0b28dbdeb2849e8443ce90ec9517ff` (lokale Git-revisie gecontroleerd), onder `.tmp/mib2q-carplay-rgi`:

- **R-hook:** `hook/routeguidance/rgd_hook.c` — Identify, abonnement, transport, lifecycle, cache en generatie.
- **R-TLV:** `hook/routeguidance/rgd_tlv.h/.c` — velddefinities en parsing.
- **R-state:** `java_patch/com/luka/carplay/rgd/RouteGuidance.java` — routeautoriteit, dirty/retry, selectie en presentatie.
- **R-BAP:** `java_patch/com/luka/carplay/rgd/BAPBridge.java` — BAP-uitvoer, teksten, rijstroken, ETA, bargraph en takeover.
- **R-map:** `java_patch/com/luka/carplay/rgd/ManeuverMapper.java`, `ManeuverPresentation.java`, `SideStreets.java`.
- **R-render:** R-BAP plus `maneuver_render/` — eigen getekende manoeuvrepresentatie.

Aanvullende referentie: Fifthbro MH2P, lokale checkout `build/refs/fifthbro-mh2p-cluster`, commit `c73765097e20d2b38ee158e5106a475f58464107`; `lsd/de/audi/app/terminalmode/smartphone/carplay/CarPlayClusterIntegration.java`. Gebruikt voor aankomstgrens/-hold; niet als bewijs dat MH2P-klassen op MU1417 kunnen worden geïnstalleerd.

Porsche-bronnen:

- **P-hook:** `native/porsche_rgi_hook.c` — huidige oorspronkelijke transportketen plus passieve lifecycle-tick.
- **P-parser:** `native/porsche_rgi.c/.h` — wire parsing, caches, selectie, mapping, lifecycle, CWRG4.
- **P-Java:** `java/de/audi/tghu/navi/app/cluster/PorscheRouteGuidance.java` — OEM-BAP-aanroepen, poll/retry, presentatie.
- **P-build:** `build-tools/build.py`, `BuildPorscheHooks.java`, `split_hmi_bridge.py`, `recover_destination_api.py`.
- **P-firmware:** `build/CombiBAPListener.javap.txt`, `build/destination-api.javap.txt`, `build/destination-wire.javap.txt` — lokaal herstelde originele MU1417-klassen. Build-output is niet gecommit.

**Status:** **Ja** = genoemde afgebakende functie aanwezig volgens referentiesemantiek; **Deels** = ontbrekende subfunctie of afwijkende randgevallen; **Nee** = geen implementatie in deze kandidaat; **Anders** = bewuste/platformgebonden vervanging. Ja betekent niet fysiek bewezen of volledige featurepariteit.

## 1. Protocol, ontvangst en sessieautoriteit

| Functie | Status | Concrete vergelijking / codebewijs |
|---|---|---|
| Route Guidance-component adverteren in Identify | Deels | P-hook `ident_hook`, P-parser `cw_rgi_component` voegen component 0x10 toe via OEM-builder. R-hook hergebruikt/vervangt een bestaand component en bewaakt capaciteit/groei. Die volledige duplicaat-/hergebruiklogica ontbreekt. |
| Start-abonnement 0x5200, component/source/exitopties | Ja | `cw_rgi_start` gebruikt dezelfde component-ID-TLV en lege presence-TLV's 1/2/3 als R-hook `rgd_request_updates`. Alleen berichtinhoud als Ja, niet transportveiligheid. |
| Veilig verzendmoment en retrybeleid | Deels | R-hook zendt vanuit geschikte transport-/heartbeatcontext, eerst 5×2s dan 30s. P-hook behoudt oorspronkelijke synchrone send vanuit RX met 2s-gate; geen backoff. De verworpen TX-proef is niet de huidige kandidaat. Dit blijft een risico. |
| Actief abonnement stoppen, 0x5203 uitsturen | Nee | R-hook `rgd_stop_updates` stuurt 0x5203. P-hook heeft geen stop-sendfunctie. Java/BAP wissen is geen protocolafmelding. |
| Inkomende 0x5203 afhandelen | Deels | P-parser `cw_rgi_consume_at` bevat clear, maar P-hook `inspect_packet` geeft alleen 0x5201/0x5202/0x5204 door. Parserondersteuning is dus niet end-to-end aangesloten. |
| Basisvalidatie 0x5201/02/04 en TLV-lengtes | Ja | P-parser `valid`, `tlv_next` en nested-lanegrenzen; lokale malformed-packetfixtures. Geen claim dat alle optionele TLV-velden zijn geport. |
| Routebron en appwissel | Ja | `parse_update` verwerkt sourceName eerst, bewaart late eerste bronlabeldata en wist bij echte bronwissel de oude routecache. |
| Bron ondersteunt geen guidance | Ja | `source_supports_rg=0` hard-cleart in `cw_rgi_consume_at`, overeenkomend met referentie-intentie. |
| `visibleInApp` als presentatiestuurveld | Deels | Native leest het, maar CWRG4 geeft het niet door aan P-Java en er is geen eigen presentatieregel voor. Geen volledige port van bron-/zichtbaarheidsautoriteit. |
| Component-ID's/multiple-component routing | Nee | Referentie leest componentinformatie; P-parser negeert component-ID-TLV's. Vast component 0x10 is geen algemene componentselectie. |
| Routegeneratie / verouderde asynchrone frames afwijzen | Deels | R-hook/R-state gebruiken monotone route_generation en afwijzen oude generaties. P gebruikt epoch, bronreset en atomische snapshot, maar geen gelijkwaardige monotone routegeneratiecontrole over proces-/routewissels. Architectuur verschilt (file versus bus). |
| CRC/atomische communicatie native naar Java | Anders | CWRG4-file + CRC/rename versus referentie-CarplayBus. Functionele vervanging, geen directe bus-port. |

## 2. Manoeuvres, hoeken, afstand en voortgang

| Functie | Status | Concrete vergelijking / codebewijs |
|---|---|---|
| Actuele manoeuvre uit eerste lijstitem kiezen | Ja | P-parser `parse_update`, `select_maneuver`; R-map `ManeuverPresentation.currentSlot`. Niet het tweede/volgende item. |
| Prefetch opslaan zonder volgende pijl te activeren | Ja | `parse_maneuver` wijzigt alleen geselecteerde descriptor; onbekende actuele payload geeft geen geleende toekomstige pijl. |
| Lange routes / volledige uint16-ID's | Anders | P heeft 64 identity-tagged manoeuvre-cacheplaatsen; referentie 32 slots met eigen mapping. Niet gelijk qua capaciteit, wel actuele identiteit beschermd. |
| Afwezige velden bij deltaberichten behouden | Ja | P-manoeuvrevelden blijven staan bij ontbrekende TLV; bron-/cursorwisseling begrenst hergebruik. |
| Expliciet lege manoeuvrelijst wissen | Ja | Lege TLV0x0d wist selectie; afwezige TLV is geen clear. |
| Manoeuvretotaal/count=0 zonder lijst | Deels | Referentie neemt maneuverCount mee in autoriteit/clear-/lanevoorwaarden. P bewaart count niet apart. Niet alle count/list-combinaties zijn gelijkwaardig. |
| 54 basistypen naar BAP-symbool/richting | Ja | `map_maneuver`; 4536 onafhankelijke referentievectoren via `test_rgi_mapping.c`. Dit dekt niet alle aanvullende geometrie of presentatie. |
| Rotonde-afrithoek, signed graden en verkeerszijde | Ja | Mapper gebruikt werkelijke hoek en junction/rijzijde, geen afritnummer als hoek. Afgebakende type/richtingmatrix komt overeen met de geteste referentiegevallen. |
| Volledige rotonde-/kruispuntzijtakken | Nee | Referentie `SideStreets.calcSideStreetsBytes` verwerkt junction_angles/TLV0x0a. P negeert manoeuvre-TLV0x0a en bouwt descriptor met `new byte[0]`. De rotondehoekfix is dus NIET de volledige kruispuntgeometrie-port. |
| Aanwezigheid van manoeuvrehoek apart bewaren | Deels | Referentie heeft `mTurnAnglePresent`; P heeft sentinel 1000 maar geen apart aanwezigheidsveld. Niet alle ontbreken/waarde-combinaties zijn afzonderlijk bewezen. |
| Z-level van manoeuvre doorgeven | Deels | P wire/Java/descriptor hebben z, maar P-parser vult geen echte z-levelbron; effectieve waarde blijft 0. Referentie-Java kan z_level ontvangen/doorgeven; de geraadpleegde iAP2-TLV-parser heeft zelf geen apart z-level-TLV. |
| Afstand koppelen aan actuele cursor | Ja | Cursorwisseling maakt oude afstand ongeldig vóór deltaparsing, onafhankelijk van TLV-volgorde. |
| Follow/Prepare/Action uit afstand | Deels | 1500/3000m, staplengteheuristiek en 15%-actievenster geport in `presentation`. Referentie bewaart ook approach-state bij tijdelijk ontbrekende afstand; P heeft die volledige latch niet. |
| Google Maps zonder staplengte | Ja | Actievenster valt terug op policycap als geen positieve stepDistance bestaat, overeenkomstig `getBargraphDenominatorM`. |
| Bargraph 0..100 in actievenster | Ja | P-Java `presentation`; geen 0..255 over een willekeurig kilometervenster. |
| Knipperende bargraph in laatste 20% | Nee | Referentie `startActionBlinkThread`/`sendActionBlinkTick`, 600ms. Geen equivalente blink-state of worker in P. |
| Tijdelijk ontbrekende afstand vasthouden | Deels | Referentie `replayDistanceToManeuver` en transientNoDistance-gate. P bewaart afwezige TLV-delta maar heeft geen gelijkwaardige BAP-replay bij expliciet onbruikbare afstand. |
| iOS `maneuver_state` TLV0x02 verwerken | Nee | R-TLV/R-state bewaren dit; P-parser leest TLV0x02 van 0x5201 niet. P berekent BAP-fase uit afstand/type. |
| Verre manoeuvres Next/Straight | Deels | Default Next en Java-property `guidanceFarStraight` aanwezig. Geen referentie-menu-/settingsintegratie of bijbehorende bediening. |

## 3. Rijstrookbegeleiding

| Functie | Status | Concrete vergelijking / codebewijs |
|---|---|---|
| Afzonderlijke lane-events, selectie op ID | Ja | `parse_lanes`, `select_lanes`: expliciet lane-index, fallback gekoppelde manoeuvre; toekomstig event verdringt actuele weergave niet. |
| Lane-cachecapaciteit en complete/incomplete eventstatus | Deels | P: 8 eventcacheplaatsen, maximaal 12 lanes, 16 hoeken/lane. Referentie heeft afzonderlijke `lgLaneComplete`/cachemapping en andere limieten. Die volledigheidsmetadata wordt niet gelijkwaardig doorgegeven. |
| Tonen/verbergen op iOS laneGuidanceShowing | Deels | Expliciete showing is aangesloten, onbekend is verborgen. Referentie heeft bovendien count/route-gates; maneuverCount ontbreekt bij P. |
| Signed lanehoeken naar BAP-codes | Ja | P-Java `laneDirection` gebruikt dezelfde negen hoekkeys/codes als R-BAP. Wire65491 wordt -45 graden, niet BAP-code65491. |
| Extra lanerichtingen / onbekende sentinel | Deels | P geeft extra richtingen door, ontdubbelt/sorteert en onderdrukt aanbeveling bij ongeldige primary. Niet alle native-key-exclusie/fallbackcombinaties uit R-BAP zijn onafhankelijk tegen een oracle getest. |
| Lane-aanbeveling en positie | Deels | Aangesloten via `NavLaneGuidanceData`; grote/ongeldige positie krijgt ordinalfallback. OEM-lay-out en volledige referentierandgevallen zijn niet fysiek bewezen. Geen appspecifieke pixeloffset. |
| Beschrijvende lane-tekst | Nee | Lane-message description/TLV3 niet naar tellertekst geport. |

## 4. Tekst, bestemming, afstand en tijd

| Functie | Status | Concrete vergelijking / codebewijs |
|---|---|---|
| Huidige straat op originele positieveld | Anders | P `setCurrentStreet(currentRoad)` behoudt werkelijke straat. Referentie gebruikt dit veld ook voor latched volgende weg/signpost. Bewust niet blind overgenomen na gebruikersmelding over verkeerde huidige positie. |
| Volgende straat/afrittekst lezen en kiezen | Deels | P-parser bewaart `turn_to` met prioriteit exitInfo > afterRoad > description. P-Java leest dit maar stuurt het niet naar een afzonderlijk tekstveld. Opslaan is GEEN zichtbare port. |
| Signpostdecoratie, colon-normalisatie en tekstscroll | Nee | Referentie `updateLatchedRouteText`, `CurrentPositionScroll`, `normalizeRouteText`, `keepLastColonPart`. Geen volledige equivalent in P. |
| Bestemmingsnaam/-adres, BAP46 | Ja | Toegevoegd via firmwarebewezen `setDestinationInfo`, dezelfde zeven-stringconstructorpositie en 50 UTF-8-bytebegrenzing. Test met echte herstelde OEM-dataklassen; schermpositie nog onbevestigd. |
| Resterende routeafstand | Ja | P leest TLV7 en roept bestaande Porsche `setRgDistanceToNextDestination` aan. OEM formatteert de eenheden; niet de referentieformatter gekopieerd. |
| Resterende reistijd | Deels | TLV6 wordt doorgegeven als duur via `setRgTimeToNextDestination(...,false,...)`. Referentie publiceert absolute ETA/type1. Dit is een werkelijk uitvoerverschil, niet volledige pariteit. |
| Rechtstreekse ETA-TLV5 | Nee | P-parser leest ETA niet. R-state/BAP gebruiken expliciete ETA of afleiding uit resterende tijd. |
| Lokale tijdzone en 12/24-uursformaat voor ETA | Nee | Referentie `HuTime`, `getHuNavigationTimeFormat`, `publishTimeToDestinationForMode`; geen equivalente P-keten. Niet ongecontroleerd MH2P-tijdcode kopiëren. |
| Afstandsstrings/-units uit iOS | Anders | P leest numerieke meters en gebruikt OEM-afstandsfuncties; iOS string/unit-TLV's 8/9/0b/0c niet verwerkt. Werking in andere voertuig-eenheden niet fysiek bevestigd. |
| Wisselen tekstmodus: weg / ETA / reistijd | Nee | Referentie infoPhase, OK/toggle, terugvaltijd en kleine/grote weergave. Geen guidance-info-toggle in P. Zoom is een aparte feature en telt niet als deze functie. |

## 5. Stoppen, aankomst en herberekenen

| Functie | Status | Concrete vergelijking / codebewijs |
|---|---|---|
| RS0 met 800ms debounce | Deels | Parser heeft de referentiedeadline; huidige P-hook tikt alleen bij ontvangen linktraffic. Referentie heeft autonome periodieke tick. Bij volledige stilte geldt P-Java freshness, niet gegarandeerd 800ms. |
| Herberekenen RS5 -> RS0 niet meteen beëindigen | Deels | Pending zonder eigen zerodeadline, actieve vervolgdata schoon hervatten. Niet alle bron-/generatie-/countgrenzen uit R-state zijn geport. |
| Loading/locating/proceed-to-route (RS3/4/6) | Deels | Status wordt numeriek geaccepteerd, maar P behandelt niet-nul grotendeels als active. Geen volledige specifieke referentiepresentatie. |
| Aankomstsymbool niet vroeg door prefetch | Ja | Fifthbro70m/explicietRS2-gate in P-Java. Dit is een aanvullende Fifthbro-port, geen claim dat beide referenties identieke complete arrival-state hebben. |
| Expliciete aankomst RS2, adres vasthouden | Ja | Native ARRIVED-descriptor, lanes/routecijfers nul; P-Java levert DestinationInfo bij active arrival. Fysieke acceptatie nog niet bevestigd. |
| Aankomst ongeveer 5s tonen, daarna wissen | Deels | Fifthbro-hold in parser, maar expiratie alleen op RX-traffic; stiltecaseduur kan door Java freshness afwijken. Geen nieuwe onafhankelijke timer in kandidaat. |
| Herhaalde aankomst niet verlengen/herleven | Ja | Monotone deadline en end_reason in `cw_rgi_consume_at`/`cw_rgi_tick`; regressietests. |
| Nieuwe route/app maakt oude deadlines ongeldig | Ja | Parser wist routecache/deadlines bij actieve nieuwe generatie/bron. Geen volledige referentie-busgeneratieimplementatie (zie protocol). |
| BAP-routevelden wissen en retry bij fout | Ja | P-Java `clear` behandelt velden apart; incl. bestemming, afstand/tijd, lanes, manoeuvre, rgActive/GAL. Huidige positie blijft intact. |
| IdentifyRejected / harde disconnect direct clear | Deels | Identify-start publiceert reset; unload maakt state inactief. Rejected zet alleen identified=0; geen overal aangesloten expliciete event-clear. Abrupte procesuitval/stilte valt terug op freshness/read-grace. |

## 6. Uitvoer, herstel en aanvullende referentiefuncties

| Functie | Status | Concrete vergelijking / codebewijs |
|---|---|---|
| OEM-guidance actief maken | Anders | P gebruikt firmwarebewezen `setGALState`, `setViewMode`, `setRgActive` en bestaande listener. Referentie eigen AppConnector/cluster-access is platformgebonden. Basis was fysiek werkend; nieuwe kandidaat niet bevestigd. |
| Hele originele routebegeleiding stoppen/takeover beheren | Deels | R-BAP `tryStopNativeNavigation`, `forceClusterRouteInfoState`, engage/disengage en startrollback. Geen gelijkwaardige complete P-implementatie; originele navi kan nog concurreren. Niet oplossen met willekeurige heartbeatintensiteit. |
| Guidance zonder actieve CarPlay-kaart tonen | Anders | P-guidance file/BAP en kaartpipeline zijn gescheiden. Geen volledige referentie `presentationReady`-/rendererReady-handshake. Kaartzichtbaarheid bewijst guidance niet en omgekeerd. |
| Pijl X/Y en eigen manoeuvre-renderer | Anders | R-render heeft eigen GL-geometry/camera. P gebruikt originele Porsche BAP-pijl, geen eigen guidance-GL-renderer of X/Y-regeling. Pixeloffsets zijn niet portbaar naar OEM-pijl. |
| Custom renderer queue/coalescing/backpressure en viewport | Nee | Geen referentie-manoeuvre-renderer geport. Bestaande CarPlay-videodecoder is een ANDERE functie. Niet als ontbrekende basis-BAP-port presenteren. |
| Guidance-heartbeat | Anders | P herpubliceert volledige OEM-uitvoer op 2s, native snapshot bij linktraffic; referentie dirty-publicatie en eigen presentatie-/blinkloops. Zelfde doel, niet dezelfde scheduler. |
| Afstandupdates vertragen/coalescen | Deels | P heeft eigen afstandsdrempels/250–2000ms-updatevensters; deze zijn GEEN aangetoonde kopie van de referentiescheduler. Semantische verandering en heartbeat omzeilen deel van die throttling. |
| Mislukte actieve uitvoer opnieuw proberen | Deels | P werkt appliedEpoch pas na succesvolle volledige update bij; volgende poll herhaalt. R-state bewaart onafhankelijke dirty masks en renderer/tekststatus. Niet per-field gelijkwaardig. |
| Diagnostiek / instellingen / persistentie | Deels | P heeft logs, bron/cursor/fase en Java-properties. Geen volledig referentiemenu, instellingenbus of complete protocoltrace. Hash-/SD-herstel is Porsche-eigen. |
| Volledige apppariteit Apple/Google/Waze | Onbewezen | Geen app-whitelist; appbronwisseling en identieke-invoertest aanwezig. Geen bewijs voor alle werkelijk geleverde route-/lane-/ETAcombinaties van alle apps. |

## Velddekking: expliciet niet volledig

Voor 0x5201 verwerkt P de route_state, currentRoad, destination, timeRemaining, distanceRemaining, distToManeuver, de eerste manoeuvre-ID, lane-index/showing, sourceName/support en visibleInApp (laatste niet naar Java). Niet gelijkwaardig verwerkt: component-ID-lijst, maneuver_state, ETA, iOS-afstandsstrings/units, manoeuvretotaal en lane-totaal.

Voor 0x5202 verwerkt P index, description, type, afterRoad, stepDistance, drivingSide, junctionType, exitAngle, linkedLane en exitInfo. JunctionElementAngles ontbreken; afstandstring/units ontbreken. ExitInfo/afterRoad halen de zichtbare tekstuitvoer nog niet.

Voor 0x5204 verwerkt P eventindex, lane-position/status/hoekvector/primary. Lane-description en aparte complete/incomplete metadata ontbreken. Alle beperkte caches en lijstlengtes zijn een implementatiegrens, geen onbeperkte pariteit.

## Belangrijkste conclusies / prioriteit

1. **Geen volledige port claimen.** Alleen type/richtingmapping heeft een onafhankelijke 4536-casesvergelijking; dit bewijst niet de zijtakken, timers, transport, ETA, tekst of fysieke lay-out.
2. **Eerst transport/lifecycle-aansluitingen afbakenen:** synchrone RX-send/backoff, protocolstop 5203, autonome stille stop/arrival, rejection/disconnect en generatieautoriteit. Werkende baseline niet opnieuw tegelijk met nieuwe transportlogica vervangen.
3. **Daarna zichtbare gaten:** junction-zijtakken (volledige rotondeweergave), tijdelijke-afstandlatch, afrit-/volgendewegtekst, absolute/lokale ETA en actionblink. DestinationInfo is inmiddels aanwezig maar pas fysiek te bevestigen.
4. **OEM-lay-out bewijzen:** originele manoeuvrepijlpositie en lanepresentatie in Apple Maps/Google Maps. Geen GL-camera-offset overnemen in de BAP-uitvoer.
5. **Optioneel/apart:** eigen guidance-renderer, routetekstscroll/info-toggle en extra referentiemenu's. Eerst bepalen of die op Porsche gewenst zijn; geen ongeautoriseerde uitbreiding.

Fysieke status: kaart en basisguidance zijn in eerdere versies door de gebruiker gezien. Deze gecorrigeerde lokale kandidaat is niet in de auto gevalideerd. Zie `CODEX_HANDOVER.md` voor actuele unit-/pakkettoestand en vorige mislukkingen.
