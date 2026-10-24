; orc - NSIS installer (per-user, no admin rights needed)
;
; Build (CI does this after packaging/stage-windows.ps1):
;   makensis /DSTAGE=<dir containing the staged orc tree's contents> `
;            /DVERSION=0.1.0 /DARCH=x86_64 installers\nsis\orc.nsi
; Defaults below match a local stage-windows.ps1 -Arch x86_64 run.

!ifndef VERSION
  !define VERSION "0.1.0"
!endif
!ifndef ARCH
  !define ARCH "x86_64"
!endif
!ifndef STAGE
  !define STAGE "..\..\dist\stage-windows-${ARCH}\orc"
!endif
!ifndef OUTFILE
  !define OUTFILE "..\..\dist\orc-${VERSION}-windows-${ARCH}-setup.exe"
!endif

Unicode true
Name "orc"
OutFile "${OUTFILE}"
InstallDir "$LOCALAPPDATA\orc"
InstallDirRegKey HKCU "Software\Nightware Labz\orc" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma

!include "MUI2.nsh"
!define MUI_ICON "..\..\branding\orc.ico"
!define MUI_UNICON "..\..\branding\orc.ico"
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "orc"
VIAddVersionKey "FileDescription" "orc - ORC (Orchestration), the Nightware Labz browser"
VIAddVersionKey "CompanyName" "Nightware Labz"
VIAddVersionKey "LegalCopyright" "Browser wrap (c) Nightware Labz; engine (LibreWolf/Gecko) MPL-2.0"

Section "orc" SEC_MAIN
  SetOutPath "$INSTDIR"
  File /r "${STAGE}\*.*"

  WriteRegStr HKCU "Software\Nightware Labz\orc" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Nightware Labz\orc" "Version" "${VERSION}"

  ; Start Menu shortcut, with the face.
  CreateDirectory "$SMPROGRAMS\orc"
  CreateShortcut "$SMPROGRAMS\orc\orc.lnk" "$INSTDIR\orc.exe" "" "$INSTDIR\orc.ico"

  ; Add/Remove Programs entry.
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\orc" "DisplayName" "orc"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\orc" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\orc" "Publisher" "Nightware Labz"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\orc" "DisplayIcon" "$INSTDIR\orc.ico"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\orc" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\orc" "UninstallString" '"$INSTDIR\uninstall.exe"'

  WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section /o "Desktop shortcut" SEC_DESKTOP
  CreateShortcut "$DESKTOP\orc.lnk" "$INSTDIR\orc.exe" "" "$INSTDIR\orc.ico"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\orc.lnk"
  Delete "$SMPROGRAMS\orc\orc.lnk"
  RMDir "$SMPROGRAMS\orc"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\orc"
  DeleteRegKey HKCU "Software\Nightware Labz\orc"
  ; The install tree goes. The profile (%APPDATA%\Nightware Labz\orc)
  ; is the user's own data - it stays unless they delete it by hand.
  RMDir /r "$INSTDIR"
SectionEnd
