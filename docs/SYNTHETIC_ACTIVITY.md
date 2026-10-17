# Synthetic activity

The static viewer can optionally animate one marker along each visible network.
The control is off by default and is labeled **Synthetic activity**.

These markers are a visual illustration of graph connectivity only. They do
not represent observed requests, message volume, throughput, latency, service
health, or any other runtime measurement. Marker count and traversal duration
are fixed and must not be interpreted as relative traffic between networks.

## Behavior

- Activity is enabled locally in the viewer and does not modify `graph.ucg.json`
  or `city.json`.
- Every visible network receives exactly one marker on the same six-second
  traversal cycle.
- A stable hash of the network ID supplies the starting phase, so markers do
  not depend on randomness or runtime data.
- Active category filters also hide the corresponding activity marker.
- The viewer disables activity when the operating system or browser requests
  reduced motion.
- Cities without networks expose the control as unavailable.

The control and its warning are included in regular, history, and
multi-repository viewers. Reloading the page returns activity to its default
off state.
