'''
Date: 2023-02-02 16:18:09
LastEditTime: 2023-02-02 16:26:55
Software: VSCode
'''
import sys

def maximizeWindow():
    if sys.platform == 'win32':
        import win32gui, win32con
        hwnd = win32gui.GetForegroundWindow()
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    else:
        pass
    
if __name__ == '__main__':
    maximizeWindow()
    
