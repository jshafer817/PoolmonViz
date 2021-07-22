.PHONY: all
all: visualize.exe

visualize.exe: visualize.py
	pyinstaller visualize.py --onefile -w --win-private-assemblies --win-no-prefer-redirects --key "@Cpbjd??E$!E8!V3U913g52HOPn9pd"
        
clean:
	del dist\visualize.exe
