"""
ui/layout.py
─────────────
Streamlit page configuration, global CSS, and JS injection.
Call apply_layout() once at the top of app.py.
"""

import streamlit as st
import streamlit.components.v1 as components


def apply_layout() -> None:
    """Set page config + inject CSS + inject auto-bullet JS."""
    st.set_page_config(page_title="Industrial Automation PMO", layout="wide")

    st.markdown(
        """
        <style>
        .main { background-color: #f8f9fa; }
        .stMetric {
            background-color: #ffffff;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
        }
        .card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 8px;
            border: 1px dotted #ccc;
            margin-bottom: 10px;
        }
        .sidebar .sidebar-content {
            background-image: linear-gradient(#2e3b4e, #2e3b4e);
            color: white;
        }
        .topic-image-container {
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Auto-bullet JS for textareas
    components.html(
        """
        <script>
        const doc = window.parent.document;
        if (!doc.getElementById("auto-bullet-script")) {
            const script = doc.createElement("script");
            script.id = "auto-bullet-script";
            script.innerHTML = `
                function pushValueToStreamlit(textarea, value, caretPos) {
                    let nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                        window.HTMLTextAreaElement.prototype, "value").set;
                    nativeInputValueSetter.call(textarea, value);
                    textarea.selectionStart = textarea.selectionEnd = caretPos;
                    textarea.dispatchEvent(new Event("input", { bubbles: true }));
                }

                document.addEventListener("keydown", function(e) {
                    if (e.target.tagName === "TEXTAREA" && e.key === "Enter") {
                        const val = e.target.value;
                        const start = e.target.selectionStart;
                        const end = e.target.selectionEnd;

                        const textBeforeCursor = val.substring(0, start);
                        const lastNewLine = textBeforeCursor.lastIndexOf("\\n");
                        const currentLine = textBeforeCursor.substring(lastNewLine + 1);

                        const bulletMatch = currentLine.match(/^(\\s*[-*•]\\s+)/);
                        if (bulletMatch) {
                            if (currentLine.trim() === bulletMatch[1].trim()) {
                                e.preventDefault();
                                const lineStart = lastNewLine !== -1 ? lastNewLine + 1 : 0;
                                const updatedValue = val.substring(0, lineStart) + val.substring(end);
                                pushValueToStreamlit(e.target, updatedValue, lineStart);
                                return;
                            }
                            e.preventDefault();
                            const bullet = bulletMatch[1];
                            const newText = "\\n" + bullet;
                            const updatedValue = val.substring(0, start) + newText + val.substring(end);
                            pushValueToStreamlit(e.target, updatedValue, start + newText.length);
                            return;
                        }

                        if (currentLine.trim() !== "") {
                            e.preventDefault();
                            const newText = "\\n- ";
                            const updatedValue = val.substring(0, start) + newText + val.substring(end);
                            pushValueToStreamlit(e.target, updatedValue, start + newText.length);
                        }
                    }
                });
            `;
            doc.body.appendChild(script);
        }
        </script>
        """,
        height=0,
        width=0,
    )