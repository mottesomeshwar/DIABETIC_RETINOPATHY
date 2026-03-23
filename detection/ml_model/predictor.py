"""
================================================================================
  FILE: detection/ml_model/predictor.py
  PURPOSE: The BRAIN of our project. This file:
    1. Loads/builds a ResNet50 deep learning model
    2. Preprocesses retinal images for the model
    3. Runs inference (prediction)
    4. Generates Grad-CAM heatmaps (visual explanation of AI's focus areas)
    5. Returns severity class + confidence score + heatmap

  DEEP LEARNING FLOW:
  Image → Preprocess → ResNet50 → Softmax → [P0, P1, P2, P3, P4]
  Grad-CAM: Backprop gradients through last conv layer → heatmap overlay
================================================================================
"""

import torch                          # PyTorch: our deep learning framework
import torch.nn as nn                 # Neural network layers
import torchvision.transforms as transforms   # Image preprocessing pipelines
import torchvision.models as models   # Pretrained models (ResNet, VGG, etc.)
import numpy as np                    # Numerical operations
from PIL import Image                 # Python Imaging Library: open/save images
import cv2                            # OpenCV: image processing (for heatmap overlay)
import os
import io
import base64
import json
import logging

# Set up a logger for this module (shows messages in the terminal)
logger = logging.getLogger(__name__)


# ==============================================================================
# CLASS: GradCAM
# PURPOSE: Generates visual explanations of the model's predictions.
# Grad-CAM works by:
#   1. Doing a forward pass to get predictions
#   2. Backpropagating the predicted class score
#   3. Computing gradient w.r.t. the LAST convolutional layer's feature maps
#   4. Weighting the feature maps by their average gradient
#   5. Producing a heatmap that highlights "where" the model looked
# ==============================================================================
class GradCAM:
    def __init__(self, model, target_layer):
        """
        Args:
            model: Our trained neural network
            target_layer: The specific conv layer we hook into (last conv layer)
        """
        self.model = model
        self.target_layer = target_layer

        # ------------------------------------------------------------------
        # Storage for gradients and activations captured by hooks.
        # Hooks let us "spy" on intermediate layer outputs during forward/back pass.
        # ------------------------------------------------------------------
        self.gradients = None
        self.activations = None

        # ------------------------------------------------------------------
        # HOOKS: Functions that run automatically during forward/backward pass.
        # register_forward_hook: Captures the OUTPUT of the target layer.
        # register_backward_hook: Captures the GRADIENTS flowing back through it.
        # ------------------------------------------------------------------
        self.target_layer.register_forward_hook(self._save_activation)
        self.target_layer.register_backward_hook(self._save_gradient)

    def _save_activation(self, module, input, output):
        """Called automatically during forward pass. Saves feature map."""
        self.activations = output.detach()   # detach() = don't track this in grad computation

    def _save_gradient(self, module, grad_input, grad_output):
        """Called automatically during backward pass. Saves gradients."""
        self.gradients = grad_output[0].detach()

    def generate(self, input_tensor, class_idx):
        """
        Generate Grad-CAM heatmap for the given class.

        Args:
            input_tensor: Preprocessed image tensor [1, 3, H, W]
            class_idx: The predicted class index (0-4)

        Returns:
            cam: A 2D numpy array (heatmap), same H×W as input image
        """
        # Step 1: Forward pass (record activations via hook)
        self.model.eval()
        output = self.model(input_tensor)  # Shape: [1, 5]

        # Step 2: Zero all existing gradients before backprop
        self.model.zero_grad()

        # Step 3: Create a one-hot vector to backprop only the target class score
        # e.g., if class_idx=2, one_hot = [0, 0, 1, 0, 0]
        one_hot = torch.zeros_like(output)
        one_hot[0][class_idx] = 1

        # Step 4: Backward pass — compute gradients w.r.t. activations
        output.backward(gradient=one_hot, retain_graph=True)

        # Step 5: Global average pooling of gradients
        # gradients shape: [1, C, H, W] → pooled: [C] (one weight per channel)
        pooled_gradients = self.gradients.mean(dim=[0, 2, 3])

        # Step 6: Weight each activation channel by its gradient importance
        activations = self.activations[0]   # Shape: [C, H, W]
        for i in range(activations.shape[0]):
            activations[i] *= pooled_gradients[i]

        # Step 7: Average across channels, apply ReLU (keep only positive values)
        cam = activations.mean(dim=0).numpy()   # Shape: [H, W]
        cam = np.maximum(cam, 0)                # ReLU: negatives → 0

        # Step 8: Normalize to [0, 1] range
        if cam.max() > 0:
            cam = cam / cam.max()

        return cam


# ==============================================================================
# CLASS: DRPredictor
# PURPOSE: Main class that ties everything together.
# Loads model, preprocesses images, runs prediction, generates heatmap.
# ==============================================================================
class DRPredictor:
    # Class-level constants
    NUM_CLASSES = 5   # 0=No DR, 1=Mild, 2=Moderate, 3=Severe, 4=Proliferative
    IMAGE_SIZE = 224  # ResNet50 expects 224×224 pixel images

    # DR class labels for display
    CLASS_LABELS = [
        'No Diabetic Retinopathy',
        'Mild DR',
        'Moderate DR',
        'Severe DR',
        'Proliferative DR'
    ]

    # Severity colors for heatmap (BGR format for OpenCV)
    SEVERITY_COLORS = {
        0: (0, 200, 0),      # Green  - No DR
        1: (255, 165, 0),    # Orange - Mild
        2: (0, 165, 255),    # Blue   - Moderate
        3: (0, 0, 255),      # Red    - Severe
        4: (128, 0, 128),    # Purple - Proliferative
    }

    def __init__(self, model_path=None):
        """
        Initialize the predictor.
        If model_path exists → load saved weights.
        Otherwise → use freshly initialized ResNet50 (for demo purposes).
        """
        # ------------------------------------------------------------------
        # DEVICE SELECTION:
        # Use GPU (CUDA) if available for faster inference, else CPU.
        # torch.cuda.is_available() checks if an Nvidia GPU is present.
        # ------------------------------------------------------------------
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Using device: {self.device}")

        # Build the model architecture
        self.model = self._build_model()

        # Load saved weights if a model file exists
        if model_path and os.path.exists(model_path):
            try:
                # map_location: load weights onto the right device (CPU/GPU)
                state_dict = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                logger.info(f"Model loaded from {model_path}")
            except Exception as e:
                logger.warning(f"Could not load model weights: {e}. Using untrained model.")
        else:
            logger.info("No saved model found. Using pretrained ResNet50 features (demo mode).")

        # Move model to chosen device and set to evaluation mode
        self.model = self.model.to(self.device)
        self.model.eval()   # eval() disables dropout & batchnorm training behavior

        # ------------------------------------------------------------------
        # GRAD-CAM SETUP:
        # Target layer = the last convolutional block in ResNet50.
        # ResNet50 architecture: conv1 → layer1 → layer2 → layer3 → layer4 → avgpool → fc
        # We hook into 'layer4' (the last residual block group).
        # ------------------------------------------------------------------
        self.grad_cam = GradCAM(self.model, self.model.layer4[-1])

        # ------------------------------------------------------------------
        # IMAGE PREPROCESSING PIPELINE:
        # Every image must go through exactly the same transformations
        # used during training for consistent results.
        #
        # 1. Resize to 224×224 (ResNet50's expected input size)
        # 2. ToTensor: PIL Image [H,W,C] uint8 → PyTorch Tensor [C,H,W] float32 in [0,1]
        # 3. Normalize: subtract mean, divide by std (ImageNet statistics)
        #    This centers the data around 0 which helps training stability.
        #    Mean/std are computed from the massive ImageNet dataset.
        # ------------------------------------------------------------------
        self.transform = transforms.Compose([
            transforms.Resize((self.IMAGE_SIZE, self.IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],   # ImageNet mean (R, G, B)
                std=[0.229, 0.224, 0.225]      # ImageNet std (R, G, B)
            )
        ])

    def _build_model(self):
        """
        Build ResNet50 modified for 5-class DR classification.

        ResNet50 Architecture Summary:
        - 50 layers deep
        - Uses 'residual connections' (skip connections) to allow very deep networks
        - Original: outputs 1000 classes (ImageNet)
        - We replace the final layer with a 5-class output

        Transfer Learning:
        - weights='DEFAULT': Load weights pretrained on 1.2M ImageNet images
        - These weights already understand edges, textures, shapes
        - We only retrain the final classification layer (faster, better results)
        """
        # Load ResNet50 with pretrained ImageNet weights
        model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)

        # ------------------------------------------------------------------
        # Replace the final fully connected (fc) layer.
        # Original: nn.Linear(2048, 1000) → 1000 ImageNet classes
        # Ours:     nn.Linear(2048, 5)    → 5 DR severity classes
        # model.fc.in_features = 2048 (ResNet50's penultimate layer size)
        # ------------------------------------------------------------------
        num_features = model.fc.in_features   # 2048
        model.fc = nn.Linear(num_features, self.NUM_CLASSES)

        return model

    def preprocess_image(self, image_path):
        """
        Load and preprocess a retinal image for model input.

        Args:
            image_path: File path (string or Path object) to the image

        Returns:
            Tuple of:
              - tensor: Processed tensor ready for model [1, 3, 224, 224]
              - original_image: PIL Image (for overlay later)
        """
        # Open image and convert to RGB (handles grayscale, RGBA, etc.)
        original_image = Image.open(image_path).convert('RGB')

        # Apply our preprocessing pipeline
        tensor = self.transform(original_image)

        # ------------------------------------------------------------------
        # unsqueeze(0): Add batch dimension.
        # Models expect input shape: [batch_size, channels, height, width]
        # Our single image: [3, 224, 224] → [1, 3, 224, 224]
        # ------------------------------------------------------------------
        tensor = tensor.unsqueeze(0)

        # Move tensor to the same device as the model (CPU or GPU)
        tensor = tensor.to(self.device)

        return tensor, original_image

    def predict(self, image_path):
        """
        Run the full prediction pipeline on a retinal image.

        Args:
            image_path: Path to the uploaded retinal image

        Returns:
            dict with keys:
              - predicted_class (int): 0-4
              - confidence (float): 0.0-1.0
              - class_label (str): Human readable label
              - probabilities (list): Probability for each class
              - heatmap_base64 (str): Base64-encoded heatmap PNG
              - severity_color (str): CSS class name
        """
        try:
            # Step 1: Load and preprocess the image
            input_tensor, original_pil = self.preprocess_image(image_path)

            # Step 2: Run forward pass with gradient tracking enabled
            # (needed for Grad-CAM backprop)
            with torch.set_grad_enabled(True):
                output = self.model(input_tensor)  # Raw logits: [1, 5]

                # ----------------------------------------------------------
                # Softmax: Converts raw logits to probabilities that sum to 1.
                # dim=1: Apply softmax across the class dimension.
                # Example logits: [2.1, -0.5, 1.3, -1.2, 0.8]
                # After softmax: [0.52, 0.04, 0.23, 0.02, 0.14] (sums to 1)
                # ----------------------------------------------------------
                probabilities = torch.softmax(output, dim=1)

                # Get the class with highest probability
                # torch.max returns (values, indices) — we want the index
                confidence, predicted_class = torch.max(probabilities, dim=1)

                # Convert from tensors to plain Python numbers
                predicted_class = predicted_class.item()   # e.g., 2
                confidence = confidence.item()             # e.g., 0.87

                # Get all 5 class probabilities as a Python list
                probs_list = probabilities[0].tolist()     # [0.05, 0.08, 0.87, 0.03, 0.02] etc.

            # Step 3: Generate Grad-CAM heatmap
            cam = self.grad_cam.generate(input_tensor, predicted_class)

            # Step 4: Overlay heatmap on original image
            heatmap_base64 = self._create_heatmap_overlay(
                original_pil, cam, predicted_class
            )

            # Step 5: Package and return all results
            return {
                'predicted_class': predicted_class,
                'confidence': confidence,
                'class_label': self.CLASS_LABELS[predicted_class],
                'probabilities': probs_list,
                'heatmap_base64': heatmap_base64,
                'severity_color': self._get_severity_css_class(predicted_class),
            }

        except Exception as e:
            logger.error(f"Prediction error: {e}", exc_info=True)
            # Return a fallback result so the app doesn't crash
            return {
                'predicted_class': 0,
                'confidence': 0.0,
                'class_label': 'Analysis Error',
                'probabilities': [0.2, 0.2, 0.2, 0.2, 0.2],
                'heatmap_base64': None,
                'severity_color': 'secondary',
                'error': str(e)
            }

    def _create_heatmap_overlay(self, original_pil, cam, predicted_class):
        """
        Overlays the Grad-CAM heatmap on the original retinal image.

        Process:
        1. Resize cam (14×14) up to match original image size
        2. Apply colormap (jet: blue=low attention, red=high attention)
        3. Alpha-blend the colormap with the original image
        4. Encode as base64 PNG string for embedding in HTML

        Args:
            original_pil: PIL Image of original retinal scan
            cam: 2D numpy array of Grad-CAM activations (14×14 from ResNet)
            predicted_class: The predicted class index

        Returns:
            base64-encoded string of the heatmap overlay PNG
        """
        # Convert PIL Image to OpenCV format (numpy array, BGR color order)
        original_cv = np.array(original_pil)
        original_cv = cv2.cvtColor(original_cv, cv2.COLOR_RGB2BGR)
        h, w = original_cv.shape[:2]

        # Resize the small CAM (e.g., 7×7) to match the full image size
        cam_resized = cv2.resize(cam, (w, h))

        # Convert to uint8 (0-255 range) for colormap application
        cam_uint8 = np.uint8(255 * cam_resized)

        # Apply JET colormap: blue=low importance, green=medium, red=high
        heatmap_colored = cv2.applyColorMap(cam_uint8, cv2.COLORMAP_JET)

        # Alpha blend: 60% original image + 40% heatmap
        # Result looks like: original image with colored hotspots overlaid
        alpha = 0.6
        overlay = cv2.addWeighted(original_cv, alpha, heatmap_colored, 1 - alpha, 0)

        # Convert the overlay back to PIL Image format
        overlay_rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
        overlay_pil = Image.fromarray(overlay_rgb)

        # Save to an in-memory buffer (no file needed)
        buffer = io.BytesIO()
        overlay_pil.save(buffer, format='PNG')
        buffer.seek(0)   # Rewind to the beginning of the buffer

        # Encode buffer bytes as base64 string (safe for embedding in HTML src)
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')

        return img_base64

    def _get_severity_css_class(self, predicted_class):
        """Returns Bootstrap CSS color class for the severity level."""
        css_classes = {
            0: 'success',   # Green
            1: 'info',      # Cyan/Blue
            2: 'warning',   # Yellow
            3: 'danger',    # Red
            4: 'dark',      # Dark (most severe)
        }
        return css_classes.get(predicted_class, 'secondary')


# ==============================================================================
# MODULE-LEVEL: Create a single shared predictor instance.
# This is loaded ONCE when Django starts up (not on every request).
# Reusing the same instance saves memory and startup time.
# ==============================================================================
_predictor_instance = None

def get_predictor():
    """
    Returns the shared DRPredictor instance (Singleton pattern).
    Creates it on first call, then reuses for all subsequent calls.
    """
    global _predictor_instance
    if _predictor_instance is None:
        from django.conf import settings
        model_path = getattr(settings, 'MODEL_PATH', None)
        _predictor_instance = DRPredictor(model_path=model_path)
    return _predictor_instance
