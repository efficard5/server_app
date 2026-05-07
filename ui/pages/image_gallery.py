# ui/pages/image_gallery.py
import streamlit as st
import os
from services.storage_service import save_file_to_server, get_files_for_topic, remove_file

def render(ctx: dict) -> None:
    st.header("🖼️ Dashboard Image Gallery")
    st.markdown("Manage your subsystem images. Files are stored on the personal server and linked to your account.")
    
    # Get current user from session state
    current_user = st.session_state.get("auth_name", "Unknown")
    is_admin = st.session_state.get("role") == "Admin"
    
    projects = ctx["projects"]
    topics = ctx["topics"]
    
    # 1. Upload Form
    with st.expander("➕ Upload New Image to Server", expanded=True):
        fcol1, fcol2 = st.columns(2)
        up_proj = fcol1.selectbox("Target Project", projects)
        up_topic = fcol2.selectbox("Target Subsystem/Topic", topics)
        uploaded = st.file_uploader("Upload Image Payload", type=["png", "jpg", "jpeg", "webp"])
        
        if st.button("💾 Save to Personal Server"):
            if uploaded:
                # Save using storage service with user tracking
                success, error = save_file_to_server(
                    uploaded, 
                    up_proj, 
                    up_topic, 
                    note=f"Uploaded by {current_user}", 
                    f_type="Dashboard Image",
                    uploaded_by=current_user
                )
                
                if success:
                    st.success(f"Success! Image saved to server and linked to {current_user}.")
                    st.toast(f"✅ File stored on server", icon="💾")
                else:
                    st.error(f"Upload failed: {error}")
                
                import time
                time.sleep(1)
                st.rerun()
            else:
                st.error("Please load a file first.")

    st.divider()
    st.subheader("Your Stored Images")
    
    # Selection for filtering display
    scol1, scol2 = st.columns(2)
    view_proj = scol1.selectbox("View Project", projects)
    view_topic = scol2.selectbox("View Subsystem", topics)
    
    # Fetch files from DB filtered by user (Admin sees everything, others see only theirs)
    user_filter = None if is_admin else current_user
    display_files = get_files_for_topic(view_proj, view_topic, user_filter=user_filter)

    if display_files:
        gcols = st.columns(3)
        for i, f_rec in enumerate(display_files):
            # f_rec: (id, file_name, local_path, url, note, type, uploaded_by)
            f_id, f_name, f_path, f_url, f_note, f_type, f_owner = f_rec
            
            with gcols[i % 3]:
                st.markdown(f"**{f_name}**")
                if f_path and os.path.exists(f_path):
                    st.image(f_path, use_container_width=True)
                else:
                    st.warning("File not found on disk")
                
                st.caption(f"Owner: {f_owner}")
                if st.button(f"🗑️ Delete", key=f"del_{f_id}"):
                    if remove_file(f_id, f_path):
                        st.success("Deleted")
                        st.rerun()
                    else:
                        st.error("Delete failed")
                st.markdown("---")
    else:
        st.info(f"No images found for {view_proj}:{view_topic} belonging to you.")
