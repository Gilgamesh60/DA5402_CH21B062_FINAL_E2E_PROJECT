"""Feature engineering for stock sentiment.

Versioned independently of the model package so feature logic can evolve
without retraining lockstep. The version string below is stamped onto
every persisted vectorizer, so downstream code can detect feature/model
version mismatches.
"""

__version__ = "0.2.0"  # bumped from 0.1.0 in when real features landed
