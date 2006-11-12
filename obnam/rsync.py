import subprocess


def compute_signature(filename):
    """Compute an rsync signature for 'filename'"""
    p = subprocess.Popen(["rdiff", "--", "signature", filename, "-"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate(None)
    if p.returncode == 0:
        return stdout
    else:
        return False


def compute_delta(signature, filename):
    """Compute an rsync delta for a file, given signature of old version"""
    p = subprocess.Popen(["rdiff", "--", "delta", "-", filename, "-"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate(signature)
    if p.returncode == 0:
        return stdout
    else:
        return False
