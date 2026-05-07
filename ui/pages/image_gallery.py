# ui/pages/image_gallery.py
import streamlit as st
import os

def render(ctx: dict) -> None:
    st.header("🖼️ Dashboard Image Gallery")
    st.markdown("Manage the subsystem images that automatically display below dashboard gauges.")
    
    projects = ctx["projects"]
    topics = ctx["topics"]
    
    # Target directory for dashboard images
    IMG_DIR = "data/topic_images"
    os.makedirs(IMG_DIR, exist_ok=True)
    
    # 1. Upload Form
    with st.expander("➕ Link New Image to Dashboard Target", expanded=True):
        fcol1, fcol2 = st.columns(2)
        up_proj = fcol1.selectbox("Target Project", projects)
        up_topic = fcol2.selectbox("Target Subsystem/Topic", topics)
        uploaded = st.file_uploader("Upload Image Payload", type=["png", "jpg", "jpeg", "webp"])
        
        if st.button("💾 Save to Graphic Engine Directory"):
            if uploaded:
                img_path = os.path.join(IMG_DIR, f"{up_proj}_{up_topic}.png")
                with open(img_path, "wb") as f:
                    f.write(uploaded.getbuffer())
                st.toast(f"✅ Image linked to {up_proj} : {up_topic}", icon="🖼️")
                st.success(f"Success! Image locked to '{up_proj} : {up_topic}'.")
                import time
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Please load a file first.")

    st.divider()
    st.subheader("Currently Active Directory Images")
    
    existing_images = sorted([f for f in os.listdir(IMG_DIR) if f.endswith(".png")])
    if existing_images:
        gcols = st.columns(3)
        for i, img_file in enumerate(existing_images):
            caption_str = img_file.replace(".png", "").replace("_", " : ")
            with gcols[i % 3]:
                st.markdown(f"**{caption_str}**")
                st.image(os.path.join(IMG_DIR, img_file), use_container_width=True)
                if st.button(f"🗑️ Erase Link", key=f"del_{img_file}"):
                    os.remove(os.path.join(IMG_DIR, img_file))
                    st.rerun()
                st.markdown("---")
    else:
        st.info("The graphics directory is currently empty.")
