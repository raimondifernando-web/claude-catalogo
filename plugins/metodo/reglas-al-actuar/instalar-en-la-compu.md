---
herramientas: Bash|PowerShell|Write|Edit|MultiEdit
patron: launchctl\s+(load|bootstrap|enable|submit|kickstart)|LaunchAgents[/\\][^\s]*\.plist|LaunchDaemons[/\\][^\s]*\.plist|crontab\s+(?!-l\b)\S|schtasks\s+/create|Register-ScheduledTask|systemctl\s+(--user\s+)?enable
---
Vas a dejar algo que arranca solo en la computadora (regla 3: lo que corre solo en tu computadora lleva el OK de la persona).
1. Pedí el OK en el chat para ESE programa, diciendo cuándo corre, qué hace y cómo se apaga.
2. Registralo en el mismo acto donde la casa lleva la lista de rutinas, con su línea «Disparador:».
3. Si el sistema lo frena, no le busques la vuelta: dejale a la persona el comando exacto para que lo corra ella.
