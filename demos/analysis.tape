# The renderer replaces RUN_ID with a validated run produced by execution.tape.
Require ttyd
Require ffmpeg
Set Shell bash
Set FontFamily "Menlo"
Set FontSize 18
Set Width 1100
Set Height 640
Set Padding 18
Set Framerate 12
Set TypingSpeed 8 ms
Set Theme "GitHub Dark"
Output docs/assets/analysis.gif
Hide
Type "export PS1='dramdpnd $ ' && clear"
Enter
Show
Type "./bin/dramdpnd verify __RUN_ID__"
Enter
Wait+Screen /VALID/
Sleep 1 s
Type "./bin/dramdpnd analyze __RUN_ID__ --summary"
Enter
Wait+Screen /Source evidence:/
Sleep 2 s
Type "./bin/dramdpnd figures __RUN_ID__"
Enter
Wait+Screen /runs\/derived\//
Sleep 1 s
Type "./bin/dramdpnd ui --no-open"
Enter
Wait+Screen /runs\/workbench\/index.html/
Sleep 3 s
