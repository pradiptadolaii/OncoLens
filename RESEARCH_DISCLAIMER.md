# OncoLens — Research-Only Disclaimer

OncoLens is an experimental brain MRI image
classification application.

It uses a ResNet18 model with four output labels:

- glioma
- meningioma
- notumor
- pituitary

The application is intended for research,
education, and technical demonstration only.

It must not be used for:

- Clinical diagnosis
- Patient treatment
- Medical decision-making
- Emergency assessment

Scientific limitations:

1. Original training-time class mapping has
   not been independently verified.

2. Independent patient-level accuracy has
   not been established.

3. External four-class accuracy has not
   been established.

4. Clinical validation has not been established.

5. Softmax outputs must not be interpreted
   as calibrated clinical probabilities.

Only use appropriately de-identified
research images with permission.
