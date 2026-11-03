# Porsche CarPlay cluster — fysieke basislijn

Vastgelegd op 3 november 2026 voor `MHI2_ER_POG24_K5137_MU1417`.

## Fysiek bevestigd

- CarPlay-video wordt ontsleuteld en als geldige H.264/AVCC-stroom ontvangen.
- Apple Maps en Google Maps zijn zichtbaar op het rechter instrumentenscherm.
- De werkende alternatieve videogeometrie is `800 × 480`.
- De renderer gebruikt display 1 en context 70.
- `--run` blijft actief zolang de CarPlay-bron bestaat; de eerdere proeflimiet van
  120 seconden is niet nodig.
- Na stoppen van de begrensde proef keert de originele Porsche-kaart terug.
- De originele `dio_manager` en `dio_manager.cw-stock` waren tijdens validatie
  bytegelijk met SHA-256
  `9c1ecb4fb2f9f8d23c40be84daada9391019da2436f684a2e88d607093af46e8`.

## Bewezen payloads

- renderer: `950107cb71eb13127175e9c5a29e3e387b74aac18e9a161f936c894aedf51072`
- receiver: `40b489be4a6a299c5e7aa83d850138ffcffb122d4d1adc6ea46ed8ba9b69f7e1`
- geometrie-helper: `af1c407e4693447903283e800484e82bacf269dee8d6a72e21176e3e7b6fa9a7`

## Laatste fysieke logstatus

```text
FIRMWARE_VERIFIED K5137 MU1417
CARPLAY_GEOMETRY_PRIMED
CARPLAY_SOURCE_STATE alive=1 valid=1
CARPLAY_WORKER_STARTED original=72 size=800x480
CARPLAY_ACTIVE display=1 context=70 size=800x480
```

## Nog opnieuw fysiek valideren

De permanente installatielaag die de bewezen payload bij iedere volgende
CarPlay-verbinding automatisch start, inclusief begrensde persistente logging en
de Online Menu-acties voor status en herstel. Deze laag verandert de bewezen
native payloads niet.
