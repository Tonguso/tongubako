# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 13:34:23 2025

@author: tongh
"""

def confirm_action(prompt="Proceed? (Y/N): "):
  """Prompts the user with a yes/no question and returns True if they answer yes, False otherwise."""
  while True:
    answer = input(prompt).strip().upper()
    if answer in ("Y", "YES"):
      return True
    elif answer in ("N", "NO"):
      return False
    else:
      print("Invalid input. Please enter Y or N.")