
import torch
import torch.nn as nn
import numpy as np

from pathlib import Path
from PIL import Image, ImageOps
from torchvision import transforms
from torchvision.models import resnet18

CLASS_NAMES = [
    "glioma",
    "meningioma",
    "notumor",
    "pituitary"
]

DEFAULT_CHECKPOINT = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "resnet18_audited_experiment_best.pth"
)

class OncoLensPredictor:

    def __init__(self, checkpoint_path=None, device=None):

        self.device = torch.device(
            device or (
                "cuda" if torch.cuda.is_available() else "cpu"
            )
        )

        path = Path(checkpoint_path or DEFAULT_CHECKPOINT)

        if not path.is_file():
            raise FileNotFoundError(
                f"Model checkpoint not found: {path}"
            )

        self.model = resnet18(weights=None)

        self.model.fc = nn.Linear(
            self.model.fc.in_features,
            len(CLASS_NAMES)
        )

        state = torch.load(
            path,
            map_location="cpu",
            weights_only=True
        )

        self.model.load_state_dict(state, strict=True)
        self.model = self.model.to(self.device)
        self.model.eval()

        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def predict(self, image_input):

        if isinstance(image_input, (str, Path)):
            with Image.open(image_input) as img:
                image = img.convert("RGB").copy()

        elif isinstance(image_input, Image.Image):
            image = image_input.convert("RGB").copy()

        else:
            raise TypeError(
                "Expected a file path or PIL Image."
            )

        processed = ImageOps.pad(
            image,
            (224, 224),
            color=(0, 0, 0)
        )

        tensor = self.transform(processed)
        tensor = tensor.unsqueeze(0).to(self.device)

        with torch.inference_mode():
            logits = self.model(tensor)
            probabilities = torch.softmax(
                logits, dim=1
            )[0].cpu().numpy()

        if not np.isfinite(probabilities).all():
            raise ValueError("Invalid model output")

        scores = {
            name: float(score)
            for name, score in zip(
                CLASS_NAMES, probabilities
            )
        }

        predicted_class = CLASS_NAMES[
            int(np.argmax(probabilities))
        ]

        return {
            "predicted_class": predicted_class,
            "scores": scores,
            "model": "ResNet18",
            "research_only": True,
            "medical_diagnosis": False
        }
