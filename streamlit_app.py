import streamlit as st
import pandas as pd
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import json

# Authenticate Google Drive using Streamlit Secrets
def authenticate_drive():
    # Load client secrets from Streamlit secrets
    client_secrets = {
        "client_id": st.secrets["client_id"],
        "client_secret": st.secrets["client_secret"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris": st.secrets["redirect_uris"],
    }

    # Save client secrets to a local file for pydrive
    with open("client_secrets.json", "w") as f:
        json.dump(client_secrets, f)

    gauth = GoogleAuth()
    gauth.LoadClientConfigFile("client_secrets.json")
    gauth.LocalWebserverAuth()  # Authenticate via browser
    return GoogleDrive(gauth)

# Function to upload the file to Google Drive
def upload_to_drive(drive, file_name, folder_id):
    file = drive.CreateFile({'title': file_name, 'parents': [{'id': folder_id}]})
    file.SetContentFile(file_name)
    file.Upload()
    return file['id']

# Set up the page
st.set_page_config(page_title="UCU Data Processing Tool", layout="centered")

# Add a header
st.title("UCU Data Processing Tool")
st.write("Please upload all required files below to process and save the results.")

# File upload sections
uploaded_outreach = st.file_uploader("Upload 'Member Outreach File'", type=["csv", "xlsx"])
uploaded_debrief = st.file_uploader("Upload 'Event Debrief File'", type=["csv", "xlsx"])
uploaded_approved = st.file_uploader("Upload 'Approved Applications File'", type=["csv"])
uploaded_submitted = st.file_uploader("Upload 'Submitted Applications File'", type=["csv"])

# Function to run your provided analysis code
def run_analysis(outreach_file, debrief_file, approved_file, submitted_file):
    try:
        # Load files into pandas DataFrames
        outreach_df = pd.read_excel(outreach_file) if outreach_file.name.endswith('.xlsx') else pd.read_csv(outreach_file)
        event_df = pd.read_excel(debrief_file) if debrief_file.name.endswith('.xlsx') else pd.read_csv(debrief_file)
        approved_df = pd.read_csv(approved_file)
        submitted_df = pd.read_csv(submitted_file)

        # Your Python logic starts here
        all_final_dfs = []
        schools = [
            ('UTA', 'UT ARLINGTON'), ('SCU', 'SANTA CLARA'), ('UCLA', 'UCLA'),
            ('LMU', 'LMU'), ('Pepperdine', 'PEPPERDINE'), ('Irvine', 'UC IRVINE'),
            ('San Diego', 'UC SAN DIEGO'), ('SMC', "SAINT MARY'S"), ('Davis', 'UC DAVIS')
        ]

        growth_officer_mapping = {
            'Ileana': 'Ileana Heredia', 'BK': 'Brian Kahmar', 'JR': 'Julia Racioppo',
            'Jordan': 'Jordan Richied', 'VN': 'Veronica Nims', 'vn': 'Veronica Nims',
            'Dom': 'Domenic Noto', 'Megan': 'Megan Sterling', 'Veronica': 'Veronica Nims',
            'SB': 'Sheena Barlow', 'Julio': 'Julio Macias', 'Mo': 'Monisha Donaldson'
        }

        for sheet_name, school in schools:
            outreach_df['Growth Officer'] = outreach_df['Growth Officer'].replace(growth_officer_mapping)
            events_df = event_df[event_df['Select Your School'].str.strip().str.upper() == school.upper()]

            outreach_df['Date'] = pd.to_datetime(outreach_df['Date'], errors='coerce')
            events_df['Date of the Event'] = pd.to_datetime(events_df['Date of the Event'], errors='coerce')

            matched_records = []
            for _, outreach_row in outreach_df.iterrows():
                outreach_date = outreach_row['Date']
                matching_events = events_df[
                    (events_df['Date of the Event'] >= outreach_date - pd.Timedelta(days=10)) &
                    (events_df['Date of the Event'] <= outreach_date)
                ]

                if not matching_events.empty:
                    combined_event_name = "/".join(matching_events['Event Name'].unique())
                    combined_event_location = "/".join(matching_events['Location'].unique())
                    combined_event_officer = "/".join(matching_events['Name'].unique())

                    combined_row = {
                        'Outreach Date': outreach_row['Date'], 'Growth Officer': outreach_row.get('Growth Officer', ''),
                        'Outreach Name': outreach_row.get('Name', ''), 'Occupation': outreach_row.get('Occupation', ''),
                        'Email': outreach_row.get('Email', ''), 'Date of the Event': outreach_date,
                        'Event Location': combined_event_location, 'Event Name': combined_event_name,
                        'Event Officer': combined_event_officer,
                        'Select Your School': "/".join(matching_events['Select Your School'].unique()),
                        'Request type?': "/".join(matching_events['Request type?'].unique()),
                        'Audience': "/".join(matching_events['Audience'].unique())
                    }
                    matched_records.append(combined_row)

            final_df = pd.DataFrame(matched_records)
            all_final_dfs.append(final_df)

        combined_df = pd.concat(all_final_dfs, ignore_index=True)
        combined_df.to_csv('combined_data.csv', index=False)

        # Authenticate and upload to Google Drive
        drive = authenticate_drive()
        folder_id = st.secrets["folder_id"]  # Use folder ID from secrets
        file_id = upload_to_drive(drive, 'combined_data.csv', folder_id)

        st.success(f"Data successfully saved to Google Drive! File ID: {file_id}")

    except Exception as e:
        st.error(f"An error occurred: {e}")

# Ensure all files are uploaded before processing
if st.button("Upload Files"):
    if uploaded_outreach and uploaded_debrief and uploaded_approved and uploaded_submitted:
        run_analysis(uploaded_outreach, uploaded_debrief, uploaded_approved, uploaded_submitted)
    else:
        st.error("Please upload all required files to proceed.")
