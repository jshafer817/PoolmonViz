.PHONY: all
all: visualize.exe

visualize.exe: visualize.py
	pyinstaller visualize.py --onefile --key "@Cpbjd??E$!E8!V3U913g52HOPn9pd"
        
clean:
	del dist\visualize.exe
