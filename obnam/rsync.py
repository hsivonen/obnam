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


def apply_delta(basis_filename, deltadata, new_filename):
    """Apply an rsync delta for a file, to get a new version of it"""
    p = subprocess.Popen(["rdiff", "--", "patch", basis_filename, "-",
                          new_filename],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    (stdout, stderr) = p.communicate(input=deltadata)
    if p.returncode == 0:
        return True
    else:
        return False
