ConnectWow CarPlay cluster voor Porsche PCM4 / MHI2
====================================================

Doelplatform
------------
Dit profiel is uitsluitend gebouwd voor:

  MHI2_ER_POG24_K5137_MU1417_971919360T

De installer controleert de firmware en de exacte SHA-256-hashes van de
originele MU1417 DIO- en HMI-starters. Een afwijkende unit wordt geweigerd
voordat een bestand wordt gewijzigd.

Werking
-------
* Het rechter instrumentenscherm wordt als alternatieve CarPlay-display van
  800 x 480 aangeboden.
* Apple Maps en iedere andere CarPlay-app die een alternatieve videostroom
  aanbiedt kan daar beeld tonen. De PCM kan een app zonder tweede stroom niet
  dwingen pixels te leveren.
* Zwarte, lege, beschadigde en niet-IDR-videostromen nemen de Porsche-kaart
  niet over. Bij wegvallend bruikbaar beeld wordt de OEM-context hersteld.
* iAP2 Route Guidance 0x5200..0x5204 wordt onderhandeld en verwerkt. Actieve
  route, afstand, manoeuvre en rijstroken worden via de bestaande Porsche
  CombiBAPListener aan het linker fysieke scherm aangeboden.
* De standaard Porsche-zoomrol blijft signed MapScale-stappen ontvangen. CarPlay
  vertaalt die naar de semantische iOS-opdracht 0=in / 1=uit; de kaart-app
  bepaalt daarna zelf de meterschaal die in beeld verschijnt.
* Zoomcommando's worden uitsluitend bij een verse CarPlay-videolease gestuurd,
  maximaal acht stappen gebundeld, 50 ms uit elkaar en maximaal 250 ms oud.
  Omkeren wist nog niet verstuurde stappen; een nieuwe videosessie kan nooit
  zoominput uit een vorige sessie overnemen.
* Bij een verbonden CarPlay-sessie blijven iOS-appmeldingen op het centrale
  MMI-scherm toegestaan, ook wanneer de Porsche-interface zichtbaar is. De
  MU1417 AppState-hook neutraliseert alleen navigatie-eigendom; speechmode en
  de bestaande popupfocus blijven origineel.

Bewezen op de fysieke Panamera
------------------------------
* display 1 / backend 4, 800 x 480;
* context 70 en videolaag 78;
* IPv6 CarPlay-verbinding op TCP 7001;
* Apple Maps-video zichtbaar op het rechter instrumentenscherm;
* Google Maps-video zichtbaar op het rechter instrumentenscherm;
* correcte kleurenbalken en YUV-rendering;
* terugkeer naar de originele kaart na einde of onbruikbaar beeld.

Nog fysiek te bevestigen
------------------------
De semantische RGI-keten naar de linker wijzerplaat is op de exacte firmware
en lokaal met fixtures geverifieerd, maar nog niet in de rijdende auto met een
echte manoeuvre bevestigd. Google Maps/Waze kunnen beeld leveren zonder alle
Apple Route Guidance-metadata; dan is rechts kaartbeeld mogelijk zonder native
pijl links. Apple Maps en Google Maps verwerken de semantische zoomopdracht in
de onderzochte referentie; Waze ontvangt deze wel maar kan hem app-zijdig
negeren. Dat kan de head-unit niet afdwingen zonder onveilige touch-emulatie.

Veilige SD-installatie
----------------------
Gebruik build/porsche-carplay-native-MU1417-candidate.zip als overlay over de
bestaande Online Menu SD-kaart en kies:

  OnlineMenu > CarPlay > Install CarPlay cluster (MU1417)

De installatie verifieert payload, firmware en stockhashes; maakt back-ups op
SD en unit; kopieert en herverifieert alle payloads; bewaart
dio_manager.cw-stock en lsd.sh.cw-stock; wisselt beide wrappers als laatste
atomair om; rolt beide terug bij een tussenfout; en remount het appvolume
altijd read-only.

Herstel
-------
OnlineMenu > CarPlay > Restore original DIO herstelt, ondanks de historische
naam, zowel DIO als de originele HMI-starter. Herstel weigert te schrijven als
een geïnstalleerd bestand of back-up extern gewijzigd is. Start PCM daarna
opnieuw.

Validatie
---------
De bron bevat native protocol-, sessie-, beeld-, venster- en hersteltests;
Linux runtime- en shellfixtures; Java-bytecodecontrole van exacte OEM-methodes
en classversie <= 48; een QNX 6.5 ARM EABI5-build; en ZIP/hash/ELF-pakkettests.

De installatie verandert geen hosts, certificaten, verkeer-, satelliet- of
licentie-instellingen en slaat geen ruwe telefoonvideo op.

Appmeldingen vereisen een actieve CarPlay-verbinding en toestemming op de
iPhone. Welke inhoud WhatsApp, Telegram of een andere app vrijgeeft wordt door
iOS en die app bepaald; de PCM kan verborgen meldingstekst niet reconstrueren.
