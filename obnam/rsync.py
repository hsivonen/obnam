import subprocess


def pipeline(*args):
    """Set up a Unix pipeline of processes, given the argv lists
    
    Returns a subprocess.Popen object corresponding to the last process
    in the pipeline.

    """
    
    p = subprocess.Popen(args[0], stdin=None, stdout=subprocess.PIPE)
    for argv in args[1:]:
        p = subprocess.Popen(argv, stdin=p.stdout, stdout=subprocess.PIPE)
    return p


def compute_signature(context, filename):
    """Compute an rsync signature for 'filename'"""
    p = pipeline([context.config.get("backup", "odirect-read"), filename],
                  ["rdiff", "--", "signature", "-", "-"])
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
