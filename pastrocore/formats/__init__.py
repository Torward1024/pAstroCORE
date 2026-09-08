# formats/__init__.py
"""Contracts with software nobody here controls.

A module in here turns the model into a file some other program reads, and knows that program's
vocabulary and nothing else: no Qt, no manipulator, no request. What is here is a function of
an `Observation` -- given the same observation it writes the same bytes, which is what makes a
characterization test possible at all.

Each format is reached as its own operation on the manipulator, and the `Super` that does it is
the only thing that knows both this and the request. That is deliberate: `ScheduleData` writes
what a person wants to look at, and these write a contract with a correlator. Mixing them would
give one this module's vocabulary and give the other that module's tolerance for close enough.
"""
