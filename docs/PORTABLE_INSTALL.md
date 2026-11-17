# Installatie op een andere Porsche-navigatie

Dit is een overlay voor een **bestaande, werkende Online Menu-SD-kaart**.
Het is geen firmware-update of universele MIB2/PCM-installatie.

## Ondersteuning en bewijs

Alleen Porsche Panamera-profiel `MHI2_ER_POG24_K5137_MU1417_971919360T`,
800 x 480 op het rechter instrumentenscherm. De installer controleert exacte
OEM-bestanden en displayconfiguratie. Afwijkende software en een bestaande
CarPlay-modificatie worden geweigerd voordat een volume schrijfbaar wordt.
Een andere Porsche/PCM4.1/PCM5/Audi is hiermee niet automatisch ondersteund.
De originele CarPlay-functie moet al actief en werkend zijn.

De gebruikte kaart-, guidance-, zoom-, logo- en Porsche-voorrangsartifacts zijn
op de bestaande Panamera getest. Deze nieuwe verse-installatieroute is lokaal
transactioneel getest, maar nog niet fysiek op een tweede unit. Ruststart en de
eerdere incidentele ontvangeruitval blijven aandachtspunten.
Geen VIN, gebruikersaccount, telefoondata, host-IP, hostsbestand of certificaat
wordt uit de testauto overgenomen. De eigen originele HMI van de doelunit blijft
behouden; alleen een wrapper wordt ervoor geplaatst. Er worden geen licenties,
CarPlay-activatie of ConnectWow-onlinediensten geconfigureerd.

## Stappen op SD en in de auto

1. Pak `porsche-carplay-MU1417-portable.zip` uit over de bestaande Online Menu-SD.
   Behoud de overige bestanden van die kaart. Gebruik deze verse overlay niet om
   een bestaande CarPlay-installatie te overschrijven.
2. Werk het Online Menu bij met de bestaande updatefunctie en open `CWRelease`.
3. Kies **Controleer unit**. Dit controleert payload, OEM-hashes en de echte J9-
   klasselinks. Bij een afwijking stopt het zonder installatie. Deze controle
   kan diagnostiek op SD schrijven, maar wijzigt geen autoconfiguratie.
4. Auto stil, CarPlay los: kies **Installeer geteste MU1417-versie**. De originele
   doelunitbestanden worden voor herstel opgeslagen onder
   `online/cw-release/recovery` op deze SD. Houd deze map bij deze auto; niet
   overschrijven en niet als herstelkopie voor een andere auto gebruiken.
   Er is geen automatische herstart.
5. Kies **Herstart PCM**. Zorg dat de originele kaart rechts in de teller geselecteerd is en verbind
   na de herstart CarPlay. Dit is een eenmalige
   proef: controleer kaart, zoom, routeaanwijzingen, terugkeer bij loskoppelen,
   Porsche-routevoorrang en terugkeer na stoppen van die Porsche-route.
6. Alleen als dit goed werkt: kies **Bevestig na geslaagde schermproef**. Vanaf
   dan blijft de functie bij volgende starts actief. Zonder bevestiging laadt
   de volgende volledige PCM-start de originele HMI zonder de nieuwe Java-laag.
7. Bij problemen: **Kopieer diagnostiek naar SD**. Met dezelfde kaart kun je
   **Herstel originele Porsche-startbestanden** kiezen en daarna **Herstart PCM**.
   De herstelactie behoudt de payload zodat diagnose mogelijk blijft.

Originele `dio_manager.cw-stock`, `lsd.sh.cw-stock` en
`connectwow-rgi/mm-ipod` zijn runtimeonderdelen, geen weg te gooien testrestanten.
De installatie verzamelt geen reeks historische proefback-ups op de unit.

## Bouwen en testen

Voer vanuit de repository uit:

```powershell
python build-tools/build_portable_sd.py --efs-root "PAD/NAAR/UITGEPAKTE/efs-system"
```

Deze map moet de originele `etc/eso/production/smartphone_integrator.json` en
`etc/mm/iap2.cfg` bevatten. De builder controleert de OEM-hashes en weigert
onbekende versies. Geteste artifacts komen uit `verified/mu1417-20261117`;
vervang die niet ongemerkt door een nieuwere, onbevestigde build.

Het pakket bevat geen automatische reboot en wordt niet automatisch op een
verbonden testauto geladen. Een geslaagde lokale test is geen bewijs van
fysieke werking op iedere andere unit.


Lokale controles (na het bouwen van het pakket):

```powershell
python -m pytest -q tests/test_portable_package.py
docker run --rm -v "D:\Software Development\Github\porsche-carplay:/src" -w /src qnx65-armv7:4.9 python3 tests/portable_install_transaction.py
```

De transactietest gebruikt echte legacy QNX-ksh met ge?soleerde bestanden en
vervangt alleen mounts, OEM-fixtureinhoud en de J9-proef. Hij test verkeerde OEM,
beschadigde payload, mount-/kopieer-/renamefouten, volledige en mislukte rollback,
??n proefboot, herhaalde bevestigde boots en OEM-herstel met een beschadigde
ge?nstalleerde library. Hij bootst geen GPU, iPhone of tweede fysieke teller na.
