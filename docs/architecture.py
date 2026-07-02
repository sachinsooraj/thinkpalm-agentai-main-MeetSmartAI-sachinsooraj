"""
MeetSmart AI — Architecture Diagram Generator.
Uses the `diagrams` Python library to produce a PNG architecture diagram.
Run: python docs/architecture.py
Output: docs/architecture.png
"""

import os
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

from diagrams import Diagram, Cluster
from diagrams.programming.framework import React, FastAPI
from diagrams.onprem.database import PostgreSQL as SQLiteNode  # SQLite not in this diagrams version
from diagrams.onprem.client import Users
from diagrams.generic.storage import Storage
from diagrams.generic.compute import Rack


graph_attr = {
    "bgcolor": "#050b18",
    "fontcolor": "#f1f5f9",
    "fontname": "sans-serif",
    "pad": "0.5",
    "ranksep": "0.8",
    "nodesep": "0.5",
    "splines": "ortho",
}

node_attr = {
    "fontcolor": "#f1f5f9",
    "fontname": "sans-serif",
    "fontsize": "11",
}

with Diagram(
    "MeetSmart AI - Multi-Agent Architecture",
    filename="docs/architecture",
    outformat="png",
    show=False,
    graph_attr=graph_attr,
    node_attr=node_attr,
    direction="LR",
):
    user = Users("ThinkPalm\nTeam")

    with Cluster("Frontend (React + Vite)"):
        ui = React("Booking UI\nAvailability Grid\nNotes Upload\nAction Tracker")

    with Cluster("Backend (FastAPI)"):
        api = FastAPI("REST API\n/api/*")

        with Cluster("AI Agents"):
            avail  = Rack("Availability\nAgent")
            book   = Rack("Booking\nAgent")
            invite = Rack("Invite\nAgent")
            notes  = Rack("Notes\nAgent")
            mom    = Rack("MoM\nAgent")
            remind = Rack("Reminder\nAgent")

    db      = SQLiteNode("SQLite\n(Schedule Store)")
    outputs = Storage("/outputs/\nMoM .docx files")
    samples = Storage("/samples/\n.ics files")
    smtp    = Rack("SMTP\n(Email Delivery)")

    # User -> UI -> API
    user >> ui >> api

    # API -> Agents -> Resources
    api >> avail  >> db
    api >> book   >> db
    api >> invite >> samples
    api >> notes  >> db
    api >> mom    >> outputs
    api >> remind

    # Agents -> Email
    invite >> smtp
    mom    >> smtp
    remind >> smtp

print("Architecture diagram saved to docs/architecture.png")
