# VHS runs the real bounded WMB command; the new run remains under ignored runs/.
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
Output docs/assets/execution.gif
Hide
Type "export PS1='dramdpnd $ ' && clear"
Enter
Show
Type "./bin/dramdpnd doctor"
Enter
Wait+Screen /wmb: ready/
Sleep 2 s
Type "./bin/dramdpnd wmb --relative"
Enter
Wait+Screen /wmb: SUCCESS, evidence VALID/
Sleep 2 s
Type "./bin/dramdpnd runs | head -5"
Enter
Wait+Screen /run ID/
Sleep 5 s
