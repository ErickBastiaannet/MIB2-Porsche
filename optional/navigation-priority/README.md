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

# Porsche-first navigation test candidate

Read `docs/NAVIGATION_PRIORITY.md` for the current implementation, verified
firmware events, tests and remaining physical checks. This optional tree now
contains both the pure policy and the guarded Java/native adapters.

The ordinary Java/native sources and active unit remain unchanged. Separate
builders generate a combined test JAR and native binary under
`build/navigation-priority/`. The test package is
`build/porsche-navigation-priority-MU1417-test.zip`.

This is NOT physically verified or installed. Read LEESMIJ-TEST.txt before use.
The installer requires a separate real-J9 link check before writing, exact
baseline hashes, verified backups and a one-boot ticket. No automatic reboot.
A subsequent HMI start without a ticket returns to the confirmed Java modules
and disables the native priority gate. Full binary/startup restore is included.

The actual arrival-presentation end timing still needs physical verification;
the candidate resumes after the OEM inactive-event has been processed.
No iPhone route cancellation or audio arbitration is implemented.
