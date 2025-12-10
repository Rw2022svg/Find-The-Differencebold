import streamlit as st
import google.generativeai as genai
import io, base64, traceback, requests
from PIL import Image

st.title("GenAI debug helper")

api_key = st.text_input("API key", type="password")
model_name = st.text_input("Model name", value="gemini-2.0-flash-exp")
theme = st.text_input("Theme", value="Cyberpunk Street Food Stall")
prompt = st.text_area("Prompt", value=f"Generate an image of a {theme} scene in bold line cartoon, bright colors. FULL BLEED, NO BORDERS.", height=150)

def extract_image_bytes(obj, debug=False):
    try:
        if hasattr(obj, "parts"):
            for p in getattr(obj, "parts"):
                if hasattr(p, "inline_data"):
                    data = getattr(p.inline_data, "data", None)
                    if data:
                        return data
                for attr in ("binary", "data", "image_bytes"):
                    if hasattr(p, attr):
                        data = getattr(p, attr)
                        if data:
                            return data
        if isinstance(obj, dict):
            for key in ("b64_json", "b64", "data", "image", "image_data"):
                if key in obj and obj[key]:
                    val = obj[key]
                    if isinstance(val, str):
                        try:
                            return base64.b64decode(val)
                        except Exception:
                            pass
                    elif isinstance(val, (bytes, bytearray)):
                        return bytes(val)
            for key in ("candidates", "output", "images", "parts"):
                if key in obj and isinstance(obj[key], (list, tuple)):
                    for item in obj[key]:
                        res = extract_image_bytes(item, debug=debug)
                        if res:
                            return res
        for attr in ("image", "content", "binary", "data", "b64_json", "uri", "url"):
            if hasattr(obj, attr):
                val = getattr(obj, attr)
                if isinstance(val, (bytes, bytearray)):
                    return bytes(val)
                if isinstance(val, str):
                    try:
                        return base64.b64decode(val)
                    except Exception:
                        if val.startswith("http"):
                            r = requests.get(val)
                            if r.status_code == 200:
                                return r.content
        if isinstance(obj, (list, tuple)):
            for item in obj:
                res = extract_image_bytes(item, debug=debug)
                if res:
                    return res
    except Exception:
        pass
    return None

if st.button("Run single generate"):
    if not api_key:
        st.error("Enter API key")
    else:
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            st.error("Failed to initialize model:\n" + str(e))
            st.text(traceback.format_exc())
            raise e

        st.info("Calling model.generate_content(prompt)... (check terminal for printed repr as well)")
        try:
            response = model.generate_content(prompt)
        except Exception as e:
            st.error("model.generate_content raised an exception:\n" + str(e))
            st.text(traceback.format_exc())
            raise e

        # Show a short introspection of response
        with st.expander("Response debug (expand to view)"):
            try:
                st.write("Type:", type(response))
                try:
                    # show top-level attributes (not huge)
                    attrs = {}
                    for a in dir(response)[:120]:
                        if a.startswith("_"):
                            continue
                        try:
                            attrs[a] = str(type(getattr(response, a)))
                        except Exception:
                            attrs[a] = "<unreadable>"
                    st.write("Sample attributes:", attrs)
                except Exception as e:
                    st.write("Could not list attributes:", e)
                try:
                    st.write("repr(response)[:1000]:")
                    st.text(repr(response)[:1000])
                except Exception:
                    st.write("Could not repr response")
            except Exception as e:
                st.write("Error introspecting response:", e)

        # Try to extract image bytes
        img_bytes = extract_image_bytes(response, debug=True)
        if not img_bytes:
            st.warning("No image bytes found by common extraction heuristics. See Response debug above and terminal.")
        else:
            st.success(f"Extracted {len(img_bytes)} bytes. Attempting to open as image.")
            try:
                img = Image.open(io.BytesIO(img_bytes))
                st.image(img, caption="Extracted image")
            except Exception as e:
                st.error("Could not open extracted bytes as image: " + str(e))
                st.text(traceback.format_exc())

        # Also print to terminal for easier copy/paste
        print("===== Terminal dump of response =====")
        try:
            print(repr(response)[:4000])
        except Exception:
            print("Could not repr response")
        print("===== End terminal dump =====")
