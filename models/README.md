# Research checkpoint setup

The checkpoint is not published because redistribution rights were not established by the supplied archive. Git LFS and Release assets do not resolve licensing uncertainty.

If you have authorized access to the original OncoLens project archive, copy its checkpoint to:

```text
models/resnet18_audited_experiment_best.pth
```

Otherwise, contact the repository author through their GitHub profile for an authorized distribution method. No approved public download URL currently exists. Do not substitute unrelated weights: the application requires a strict four-output state-dict load and fixed class order.

- Size: 44,792,971 bytes
- SHA-256: `4ba78eaa0302a8cf35f846316888b720fbc4ce7c5ed86946b1d8fb657e0dd3a4`

Verify with PowerShell `Get-FileHash models/resnet18_audited_experiment_best.pth -Algorithm SHA256` or Linux `sha256sum models/resnet18_audited_experiment_best.pth`.

Load only trusted, authorized checkpoints. The unchanged inference module uses `torch.load(..., weights_only=True)` and strict state-dict loading. The backend constructs the predictor during import and cannot start without the checkpoint.

If redistribution rights are established later, publish an authorized versioned Release or Git LFS artifact and update this document with its download URL and hash. Publication leaves the original checkpoint unchanged.
