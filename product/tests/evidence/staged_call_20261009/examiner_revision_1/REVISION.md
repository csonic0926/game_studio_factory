# Examiner delivery revision

The first examiner packet remains preserved and unlaunched. Twelve semantic stage
outputs and their real call records remain unchanged. This revision changes only
how the examiner receives and audits the same permitted data; no semantic stage
is rerun and no previous output is repaired.

PACKET.json contains each source and stage output once, all stage-template bytes,
exact per-stage input mappings, execution records and Candidate Q. Its prompt
reconstruction definition recreates all twelve original inline prompts byte for
byte. render_examiner_revision.py verifies that equality and the sealed output
hashes. The original expanded prompts are retained, not replaced.

An explicit single-file read is now allowed to load the examiner-only packet,
followed by no additional tools/source reads. This avoids another large manual
inline transcription/helper after the original 158582-byte inline launch blocked.
No claim is made that a host rejected the reduced payload. This is a declared
access/presentation amendment, pending fresh execution review, not hard filesystem
isolation or evidence that the examiner could not access other files. The examiner
receives no full protocol, expected findings, review verdicts or coordinator notes.

A fresh execution reviewer may check source identity and reconstruction against
original safe artifacts, but must not supply an interpretation of case outcomes
to the examiner. After that review the examiner gets only the packet path, exact
hash and neutral loading instruction. Original trial status remains incomplete
under its unchanged examiner-delivery rule. Any revised examination result is
reported under this declared revision, never as the original inline run.
