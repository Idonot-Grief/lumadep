import platform

def get_os():
    sys = platform.system().lower()
    if sys == "windows":
        return "windows"
    elif sys == "darwin":
        return "osx"
    else:
        return "linux"