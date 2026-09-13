from pathlib import Path
from teldrive_lab.media_jellyfin import classify_path, discover_filesystem, rclone_mount_command, validate_exposure

def test_media_classification():
    assert classify_path(Path("Movie.mkv")) == ("video","mkv",0.99)
    assert classify_path(Path("track.flac")) == ("audio","flac",0.99)
    assert classify_path(Path("notes.txt")) is None

def test_discovery_is_bounded_and_non_mutating(tmp_path):
    (tmp_path/"Music").mkdir(); (tmp_path/"Music"/"a.mp3").write_bytes(b"x")
    found=discover_filesystem(tmp_path,max_depth=3,max_files=10)
    assert len(found)==1 and found[0].source_path.endswith("a.mp3")

def test_rclone_boundary_is_read_only():
    command=rclone_mount_command("teldrive:root",Path("/tmp/r3-media"))
    assert "--read-only" in command and "--vfs-cache-mode" in command
    assert "copy" not in command and "move" not in command and "delete" not in command

def test_exposure_rejects_protected_overlap(tmp_path):
    protected=tmp_path/"production"; protected.mkdir()
    try:
        validate_exposure(protected, (protected,))
    except Exception as exc:
        assert "protected" in str(exc)
    else:
        raise AssertionError("protected production root was accepted")
