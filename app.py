from flask import Flask, request, render_template_string, make_response, redirect, send_file
from youtube_transcript_api import YouTubeTranscriptApi
import re
import html
from fpdf import FPDF
from io import BytesIO

app = Flask(__name__)

def extract_video_id(url):
    match = re.search(
        r"(?:v=|\/|be\/|embed\/)([0-9A-Za-z_-]{11})",
        url
    )
    return match.group(1) if match else None

@app.route('/', methods=['GET'])
def index():
    error_message = request.args.get('error', '')
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>YouTube Transcript Extractor</title>
        <style>
            :root {{
                --bg-color: #0f172a;
                --primary: #38bdf8;
                --secondary: #1e293b;
                --text-light: #f1f5f9;
                --text-muted: #94a3b8;
            }}

            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}

            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }}

            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: var(--bg-color);
                color: var(--text-light);
                padding: 40px 20px;
                max-width: 900px;
                margin: auto;
                animation: fadeIn 0.5s ease-in;
            }}

            h1 {{
                font-size: 2rem;
                margin-bottom: 20px;
                color: var(--primary);
                text-align: center;
            }}

            input[type=text], button {{
                width: 100%;
                max-width: 600px;
                display: block;
                margin: 0 auto;
            }}

            input[type=text] {{
                padding: 16px;
                font-size: 18px;
                border-radius: 10px;
                border: none;
                background: var(--secondary);
                color: var(--text-light);
                margin-bottom: 20px;
                width: 100%;
            }}

            button {{
                padding: 12px 20px;
                font-size: 16px;
                border-radius: 8px;
                background: var(--primary);
                color: white;
                border: none;
                cursor: pointer;
                transition: background 0.3s ease;
            }}

            button:hover {{
                background: #0ea5e9;
            }}

            .transcript {{
                white-space: pre-wrap;
                background: var(--secondary);
                padding: 24px;
                border-radius: 8px;
                margin-top: 30px;
                color: var(--text-light);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
                animation: fadeIn 0.6s ease-in;
            }}

            .button-group {{
                display: flex;
                flex-direction: column;
                gap: 12px;
                align-items: center;
                margin-top: 20px;
            }}

            @media (min-width: 600px) {{
                .button-group {{
                    flex-direction: row;
                    justify-content: center;
                }}
            }}
        </style>
    </head>
    <body>
        <h1>YouTube Transcript Extractor</h1>
        {'<p style="color:#ff6b6b;">' + error_message + '</p>' if error_message else ''}
        <form action="/get-transcript" method="post">
            <div style="margin-top:20px;">
                <input type="text" name="youtube_url" placeholder="https://www.youtube.com/watch?v=..." required>
            </div>
            <div style="margin-top:20px;">
                <button type="submit">Get Transcript</button>
            </div>
        </form>
        <div id="loadingSpinner" style="display:none;text-align:center;margin-top:20px;">
            <div style="border: 6px solid #f3f3f3; border-top: 6px solid var(--primary); border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin:auto;"></div>
            <p style="margin-top:10px;">Fetching transcript...</p>
        </div>
        <script>
        document.querySelector("form").addEventListener("submit", function () {{
            document.getElementById("loadingSpinner").style.display = "block";
        }});
        </script>
    </body>
    </html>
    '''

@app.route('/get-transcript', methods=['POST'])
def get_transcript():
    url = request.form.get('youtube_url')
    video_id = extract_video_id(url)
    if not video_id:
        return redirect('/?error=Invalid+YouTube+URL')

    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, VideoUnplayable
    import time
    import requests
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            break
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, VideoUnplayable) as e:
            return redirect(f"/?error=Transcript+not+available:+{html.escape(str(e))}")
        except Exception as e:
            if attempt == max_attempts - 1:
                return redirect(f"/?error=Failed+to+get+transcript:+{html.escape(str(e))}")
            time.sleep(1)

    try:
        resp = requests.get(
            f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json',
            timeout=5
        )
        resp.raise_for_status()
        video_title = resp.json().get('title', 'transcript')
    except Exception:
        print("oEmbed request failed or returned invalid JSON")
        video_title = 'transcript'

    try:
        video_title = re.sub(r'[\\/*?:"<>|]', "_", video_title)
        text = "\n".join([entry['text'] for entry in transcript])
        escaped_text = html.escape(text)
        return render_template_string(f'''
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Transcript</title>
                <style>
                    :root {{
                        --bg-color: #0f172a;
                        --primary: #38bdf8;
                        --secondary: #1e293b;
                        --text-light: #f1f5f9;
                        --text-muted: #94a3b8;
                    }}

                    @keyframes fadeIn {{
                        from {{ opacity: 0; transform: translateY(10px); }}
                        to {{ opacity: 1; transform: translateY(0); }}
                    }}

                    * {{
                        box-sizing: border-box;
                        margin: 0;
                        padding: 0;
                    }}

                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: var(--bg-color);
                        color: var(--text-light);
                        padding: 40px 20px;
                        max-width: 900px;
                        margin: auto;
                        animation: fadeIn 0.5s ease-in;
                    }}

                    h1 {{
                        font-size: 2rem;
                        margin-bottom: 20px;
                        color: var(--primary);
                        text-align: center;
                    }}

                    input[type=text], button {{
                        width: 100%;
                        max-width: 600px;
                        display: block;
                        margin: 0 auto;
                    }}

                    input[type=text] {{
                        padding: 16px;
                        font-size: 18px;
                        border-radius: 10px;
                        border: none;
                        background: var(--secondary);
                        color: var(--text-light);
                        margin-bottom: 20px;
                        width: 100%;
                    }}

                    button {{
                        padding: 12px 20px;
                        font-size: 16px;
                        border-radius: 8px;
                        background: var(--primary);
                        color: white;
                        border: none;
                        cursor: pointer;
                        transition: background 0.3s ease;
                    }}

                    button:hover {{
                        background: #0ea5e9;
                    }}

                    .transcript {{
                        white-space: pre-wrap;
                        background: var(--secondary);
                        padding: 24px;
                        border-radius: 8px;
                        margin-top: 30px;
                        color: var(--text-light);
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
                        animation: fadeIn 0.6s ease-in;
                    }}

                    .button-group {{
                        display: flex;
                        flex-direction: column;
                        gap: 12px;
                        align-items: center;
                        margin-top: 20px;
                    }}

                    @media (min-width: 600px) {{
                        .button-group {{
                            flex-direction: row;
                            justify-content: center;
                        }}
                    }}
                </style>
            </head>
            <body>
                <h1>Transcript</h1>
                <div class="button-group">
                    <div>
                        <button onclick="downloadPDF()">Download as PDF</button>
                    </div>
                    <div>
                        <form action="/" method="get" style="display:inline;">
                            <button type="submit">Get Transcript for Another Video</button>
                        </form>
                    </div>
                </div>
                <div class="transcript">{escaped_text}</div>
                <script>
                async function downloadPDF() {{
                    const text = `{escaped_text}`.replace(/&#x27;/g, "'");
                    const title = "{video_title}";

                    const response = await fetch("/download-pdf", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/x-www-form-urlencoded" }},
                        body: new URLSearchParams({{ content: text, title: title }})
                    }});

                    const blob = await response.blob();

                    if (typeof window.showSaveFilePicker === "function") {{
                        // Chrome/Edge with File System Access API
                        const fileHandle = await window.showSaveFilePicker({{
                            suggestedName: title + ".pdf",
                            types: [{{ description: "PDF File", accept: {{ "application/pdf": [".pdf"] }} }}]
                        }});
                        const writable = await fileHandle.createWritable();
                        await writable.write(blob);
                        await writable.close();
                    }} else {{
                        // Safari and fallback
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = title + ".pdf";
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                    }}
                }}
                </script>
            </body>
            </html>
            ''')
    except Exception as e:
        return redirect(f"/?error={html.escape(str(e))}")

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    text = request.form.get('content', '')
    title = request.form.get('title', 'transcript')
    title = re.sub(r'[\\/*?:"<>|\r\n\t]+', "_", title).strip()
    if not title:
        title = "transcript"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.multi_cell(0, 10, line)
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=f"{title}.pdf")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)