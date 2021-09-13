import signal, os, process_handler as ph, fcntl, sys, time

hProcess = ph.ProcessHandler()
lockfile = None

def sig_handler(signum, frame):
    print('SIGNAL RECEIVED:', signum)
    hProcess.terminate()
    if lockfile is not None:
        lockfile.close()

if __name__ == "__main__":
    os.system("taskset -p -c 0,1 %d" % os.getpid())

    try:
        lockfile_name = "/tmp/indycare_instance.lock"
        lockfile = open(lockfile_name, "w")
        fcntl.lockf(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        # another instance is running or config load failed
        sys.exit(1)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
    
    hProcess.run()

    lockfile.close()
