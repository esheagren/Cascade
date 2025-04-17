import os
import pandas as pd
import numpy as np
import duckdb
from datetime import datetime
from dagster import job, schedule, op, ScheduleDefinition
from bayesian_changepoint_detection.online_changepoint_detection import BOCD
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from settings import DATA_DIR, SLACK_WEBHOOK

class BOCPDDetector:
    def __init__(self, hazard=250):
        """
        Initialize the Bayesian Online Changepoint Detection model
        
        Args:
            hazard: Hazard rate (expected run length between changepoints)
        """
        self.hazard = hazard
        self.detector = BOCD(hazard=hazard)
        self.posterior_history = []
        
    def update(self, x: np.ndarray) -> float:
        """
        Update the detector with new data and return the changepoint probability
        
        Args:
            x: New data point or array of data points
            
        Returns:
            Probability of a changepoint at the latest timestep
        """
        if isinstance(x, (float, int)):
            x = np.array([x])
            
        # Update the model with the new data
        for val in x:
            self.detector.update(val)
            
        # Get the current posterior distribution
        posterior = self.detector.get_posterior()
        self.posterior_history.append(posterior)
        
        # Calculate the probability of a changepoint at the current timestep
        # (probability of run length being 0)
        p_cp = posterior[0]
        
        return p_cp


@op
def load_daily_indices():
    """
    Load the daily indices from DuckDB
    """
    db_path = DATA_DIR / "agidash.duckdb"
    con = duckdb.connect(str(db_path))
    
    # Get the last 180 days of data
    df = pd.DataFrame(con.execute("""
        SELECT * FROM daily_index
        ORDER BY date ASC
        LIMIT 180
    """).fetchall())
    
    if not df.empty:
        df.columns = ['date', 'capability', 'attention', 'market', 'regulatory']
    
    con.close()
    return df

@op
def detect_changepoints(df: pd.DataFrame):
    """
    Run Bayesian online changepoint detection on each index
    """
    if df.empty:
        return {}
    
    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Create a detector for each index
    detectors = {
        'capability': BOCPDDetector(),
        'attention': BOCPDDetector(),
        'market': BOCPDDetector(),
        'regulatory': BOCPDDetector()
    }
    
    # Initialize results dictionary
    results = {
        'date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
        'changepoint_probs': {}
    }
    
    # Process each index
    for index_name, detector in detectors.items():
        if index_name in df.columns:
            # Get the data for this index
            x = df[index_name].values
            
            # Remove NaN values
            x = x[~np.isnan(x)]
            
            if len(x) > 0:
                # Update the detector with all data points
                for val in x:
                    p_cp = detector.update(val)
                
                # Store the final probability
                results['changepoint_probs'][index_name] = float(p_cp)
    
    # Check if any probability exceeds the threshold
    results['alert'] = any(p >= 0.5 for p in results['changepoint_probs'].values())
    
    # Connect to DuckDB and store the results
    db_path = DATA_DIR / "agidash.duckdb"
    con = duckdb.connect(str(db_path))
    
    # Create table if it doesn't exist
    con.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            date DATE,
            capability_prob FLOAT,
            attention_prob FLOAT,
            market_prob FLOAT,
            regulatory_prob FLOAT,
            alert BOOLEAN
        )
    """)
    
    # Insert the new alert
    con.execute("""
        INSERT INTO alerts
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        results['date'],
        results['changepoint_probs'].get('capability', 0.0),
        results['changepoint_probs'].get('attention', 0.0),
        results['changepoint_probs'].get('market', 0.0),
        results['changepoint_probs'].get('regulatory', 0.0),
        results['alert']
    ])
    
    con.close()
    
    return results

@op
def send_alert(results: dict):
    """
    Send a Slack alert if a changepoint is detected
    """
    if not results.get('alert', False) or not SLACK_WEBHOOK:
        return
    
    try:
        # Initialize Slack client
        client = WebClient(token=SLACK_WEBHOOK)
        
        # Format the message
        message = f"*AGI-Perception Cascade Alert* :warning:\n\n"
        message += f"Date: {results['date']}\n\n"
        message += "Changepoint probabilities:\n"
        
        for index_name, prob in results['changepoint_probs'].items():
            message += f"- {index_name.capitalize()}: {prob:.2f}\n"
        
        # Send the message
        response = client.chat_postMessage(
            channel="#alerts",  # Specify the channel
            text=message,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
        )
    except SlackApiError as e:
        logging.error(f"Error sending Slack message: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

@job
def detect_job():
    """
    Job to detect changepoints and send alerts
    """
    indices = load_daily_indices()
    results = detect_changepoints(indices)
    send_alert(results)

@schedule(cron_schedule="0 0 * * *", job=detect_job)
def daily_detection_schedule():
    """
    Schedule to run the detection job daily at midnight
    """
    return {}

def plot_posterior(detector: BOCPDDetector, dates, values, title=''):
    """
    Plot the posterior probabilities of run lengths
    """
    if not detector.posterior_history:
        return
    
    # Stack the posteriors into a 2D array
    posteriors = np.vstack(detector.posterior_history)
    
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot the posterior probabilities as a heatmap
    im = ax.imshow(posteriors.T, aspect='auto', cmap='viridis')
    
    # Set the x-axis tick labels to the dates
    ax.set_xticks(np.arange(0, len(dates), max(1, len(dates) // 10)))
    ax.set_xticklabels([d.strftime('%Y-%m-%d') for d in dates[::max(1, len(dates) // 10)]])
    
    # Set the y-axis label
    ax.set_ylabel('Run Length')
    
    # Set the title
    ax.set_title(f'Posterior Probabilities of Run Lengths - {title}')
    
    # Add a colorbar
    plt.colorbar(im, ax=ax, label='Probability')
    
    # Add a second axis below for the time series
    ax2 = ax.twinx()
    ax2.plot(values, 'r-', alpha=0.5)
    ax2.set_ylabel('Index Value', color='r')
    
    return fig
