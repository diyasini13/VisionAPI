import streamlit as st
from google.cloud import vision
import os
from PIL import Image , ImageDraw
import io
import auth_token
import json
import streamlit as st
import jwt
import os
from dotenv import load_dotenv
from google.oauth2 import id_token
from google.auth.transport import requests

# Set your Google Cloud credentials (replace with your actual path)
#os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path/to/credentials.json"


load_dotenv()

def authentication():
    GOOGLE_CLIENT_ID = "633630984866-qj00anvn6cu2kahus5ft1cnc4o8pe7dp.apps.googleusercontent.com"# Replace with your client ID

    def verify_token(token):
        try:
            # Verify the token with Google's servers
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)

            # Check if the token is from the correct audience (your client ID)
            if idinfo['aud'] != GOOGLE_CLIENT_ID:
                raise ValueError('Wrong audience.')

            return idinfo
        except ValueError as e:
            print(e)
            return "Invalid"
        except Exception as e:
            print(e)
            return "Error"

    # Get the token from the query parameter
    token = st.experimental_get_query_params().get("token", [""])[0]


    if not token:
        st.error("Unauthorized access. Token not provided.")
        st.stop()

    # Verify the token
    decoded = verify_token(token)

    if decoded == "Invalid":
        st.error("Invalid token. Access denied.")
        st.stop()
    elif decoded == "Error":
        st.error("Error in token verification. Access denied.")
        st.stop()
    

def detect_labels(image_content):
    """Detects labels in the provided image content."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_content)
    response = client.label_detection(image=image)
    labels = response.label_annotations

    if response.error.message:
        st.error(f"Error: {response.error.message}")
        return None

    return [{"description": label.description, "score": label.score} for label in labels]

def detect_objects(image_content):
    """Detects objects in the provided image content."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_content)
    response = client.object_localization(image=image)
    objects = response.localized_object_annotations

    if response.error.message:
        st.error(f"Error: {response.error.message}")
        return None

    return [{"name": obj.name, "score": obj.score, "vertices": [{"x": vertex.x, "y": vertex.y} for vertex in obj.bounding_poly.normalized_vertices]} for obj in objects]

def detect_faces(image_content):
    """Detects faces in the provided image content."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_content)
    response = client.face_detection(image=image)
    faces = response.face_annotations

    if response.error.message:
        st.error(f"Error: {response.error.message}")
        return None

    return [{"vertices": [{"x": vertex.x, "y": vertex.y} for vertex in face.bounding_poly.vertices], "joy": face.joy_likelihood.name, "sorrow": face.sorrow_likelihood.name, "anger": face.anger_likelihood.name, "surprise": face.surprise_likelihood.name} for face in faces]

def draw_bounding_boxes(image, vertices, color="red", width=5):  # Increased width for boldness
    """Draws bounding boxes on an image with bold lines."""
    draw = ImageDraw.Draw(image)
    for i in range(len(vertices)):
        x1 = vertices[i]["x"] * image.width if isinstance(vertices[i]["x"], float) else vertices[i]["x"]
        y1 = vertices[i]["y"] * image.height if isinstance(vertices[i]["y"], float) else vertices[i]["y"]
        x2 = vertices[(i + 1) % len(vertices)]["x"] * image.width if isinstance(vertices[(i + 1) % len(vertices)]["x"], float) else vertices[(i + 1) % len(vertices)]["x"]
        y2 = vertices[(i + 1) % len(vertices)]["y"] * image.height if isinstance(vertices[(i + 1) % len(vertices)]["y"], float) else vertices[(i + 1) % len(vertices)]["y"]
        draw.line([x1, y1, x2, y2], fill=color, width=width)
    return image

def app():
    st.title("Instant Object Detection: Vision API")

    uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        image_bytes = uploaded_file.getvalue()

        if uploaded_file is not None:
            st.subheader("Uploaded Image:")
            st.image(image)

        option = st.selectbox("Choose an operation:", ["Detect Labels", "Detect Objects", "Detect Faces"])

        if st.button("Process Image"):
            with st.spinner("Processing..."):
                if option == "Detect Labels":
                    results = detect_labels(image_bytes)
                    if results:
                        st.subheader("Detected Labels:")
                        label_texts = [f"**{label['description']}**: {label['score']:.2f}" for label in results]
                        st.write(" | ".join(label_texts))
                    elif results is not None:
                        st.warning("No labels detected or an error occurred.")

                elif option == "Detect Objects":
                    results = detect_objects(image_bytes)
                    if results:
                        st.subheader("Detected Objects:")
                        object_texts = [f"**{obj['name']}**: {obj['score']:.2f}" for obj in results]
                        st.write(" | ".join(object_texts))

                        image_with_boxes = image.copy()
                        for obj in results:
                            image_with_boxes = draw_bounding_boxes(image_with_boxes, obj["vertices"], "green")
                        st.image(image_with_boxes, caption="Objects with Bounding Boxes")
                    elif results is not None:
                        st.warning("No objects detected or an error occurred.")

                elif option == "Detect Faces":
                    results = detect_faces(image_bytes)
                    if results:
                        image_with_boxes = image.copy()
                        for face in results:
                            image_with_boxes = draw_bounding_boxes(image_with_boxes, face["vertices"], "blue")
                        st.image(image_with_boxes, caption="Faces with Bounding Boxes")
                        st.subheader("Detected Faces:")
                        for face in results:
                            st.write("Bounding Box:")
                            for vertex in face["vertices"]:
                                st.write(f"  ({vertex['x']}, {vertex['y']})")
                            st.write(f"  Joy: {face['joy']}")
                            st.write(f"  Sorrow: {face['sorrow']}")
                            st.write(f"  Anger: {face['anger']}")
                            st.write(f"  Surprise: {face['surprise']}")
                            st.write("---")
                        
                    elif results is not None:
                        st.warning("No faces detected or an error occurred.")

                if results:
                    if st.button("Display JSON"):
                        st.json(results)

if __name__ == "__main__":
    auth_token.authentication();
    app();