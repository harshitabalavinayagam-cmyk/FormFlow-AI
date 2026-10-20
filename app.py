
    for form in all_forms:

        responses = get_responses_for_form(
            form["id"]
        )

        for response in responses:

            recent_submissions.append({
                "Form": form["title"],
                "Response ID": response["id"],
                "Submitted At": response["submitted_at"]
            })

    if recent_submissions:

        recent_submissions.sort(
            key=lambda x: x["Submitted At"],
            reverse=True
        )

        recent_submissions = recent_submissions[:10]

        recent_df = pd.DataFrame(
            recent_submissions
        )

        st.dataframe(
            recent_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No submissions available yet."
        )

    # ---------------------------------------------------------
    # ANALYTICS SUMMARY
    # ---------------------------------------------------------

    st.divider()

    st.markdown("### 💡 Quick Summary")

    if total_forms == 0:

        st.info(
            "No forms have been created yet. "
            "Create a form to start collecting responses."
        )

    elif total_responses == 0:

        st.info(
            f"You currently have {total_forms} form(s), "
            f"but no responses have been submitted yet."
        )

    else:

        st.success(
            f"🎉 Your system has collected "
            f"{total_responses} response(s) "
            f"across {total_forms} form(s)."
        )


# ============================================================
# SETTINGS
# ============================================================

elif st.session_state.page == "Settings":

    st.markdown(
        '<div class="dashboard-title">Settings</div>',
        unsafe_allow_html=True
    )

    st.subheader(
        "⚙️ FormFlow-AI"
    )

    st.write(
        "AI-powered intelligent form digitization "
        "and dynamic form generation."
    )

    st.divider()

    st.subheader(
        "Supported AI Input"
    )

    st.write(
        "• Text requirements"
    )

    st.write(
        "• PDF forms"
    )

    st.write(
        "• PNG/JPG images"
    )

    st.divider()

    st.subheader(
        "Supported Field Types"
    )

    st.write(
        "Text • Textarea • Number • Email • Date • "
        "Select • Radio • Checkbox"
    )
