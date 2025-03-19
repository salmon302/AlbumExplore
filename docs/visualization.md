# Visualization Implementation

This document describes the implementation of the visualization components in the AlbumExplore project.

## Overview

The visualization system provides multiple views for exploring album data and tag relationships. The main components are:

*   **`src/gui/main_window.py`:** The main application window, which contains the tabbed interface and interacts with the `ViewManager`.
*   **`src/albumexplore/visualization/views.py`:** Contains the `create_view` function, which acts as a factory for different view types.
*   **`src/albumexplore/visualization/view_manager.py`:** Manages the different views and their interactions.
*   **`src/albumexplore/visualization/models.py`:** Contains data models for visual nodes and edges.
*   **`src/albumexplore/visualization/data_interface.py`:** Provides an interface for accessing data from the database.

## View Types

The following view types are implemented and managed by the `create_view` function in `src/albumexplore/visualization/views/__init__.py`

*   **Network View:** (`EnhancedNetworkView`) Displays a network graph of albums and tags.
*   **Table View:** (`TableView`) Displays album data in a tabular format.
*   **Arc Diagram:** (`ArcView`) Displays albums and tags in a linear arrangement with arcs representing relationships.
*   **Chord Diagram:** (`ChordView`) Displays relationships between albums and tags using a circular layout.
* **Tag Explorer View:** (`TagExplorerView`) Provides a view focused on exploring tags.
* **Tag Graph View:** (`TagGraphView`) Provides another graph-based view, possibly focused specifically on tag relationships.

## `src/gui/main_window.py`

The `MainWindow` class in `main_window.py` is responsible for:

*   Creating the main application window and the tabbed interface.
*   Handling user interactions (e.g., searching, selecting tags).
*   Loading data and updating the views.
*   Interacting with the `ViewManager` to create and manage views.
*   Creating the "Network" tab using `create_view(ViewType.NETWORK)`.

## `src/albumexplore/visualization/`

This directory contains the core visualization logic.

### `views/__init__.py`

This file contains the `create_view` function and the `view_map` dictionary.

**`create_view(view_type: ViewType, parent: Optional[QWidget] = None) -> Optional[BaseView]`:**

*   This function acts as a factory for creating view instances.
*   It takes a `ViewType` enum value as input, specifying the desired view type.
*   It uses the `view_map` dictionary to retrieve the corresponding view class.
*   It creates an instance of the view class and returns it.
*   It handles potential errors, such as an unknown view type or an exception during view creation.
* It sets default styling for new views.

**`view_map: Dict[ViewType, Type[BaseView]]`:**

*   This dictionary maps `ViewType` enum values to their corresponding view classes. This allows the `create_view` function to dynamically create different view types.

### `views/`

This directory contains the implementation of individual views.

### `view_manager.py`

The `ViewManager` class (located in `src/albumexplore/visualization/view_manager.py`) is responsible for managing the different views and their interactions. It acts as a central coordinator for the visualization system.

**Key Functionalities:**

*   **Initialization:**
    *   Initializes a `StateManager` for managing view state.
    *   Initializes a `ViewIntegrationManager` for handling interactions between views.
    *   Creates instances of different renderers (using `create_renderer`) for each `ViewType`, storing them in a dictionary.
    *   Initializes a cache for storing rendered data.

*   **`switch_view(view_type: ViewType)`:**
    *   Handles switching between different view types.
    *   Retrieves visible data from the `DataInterface`.
    *   Uses the `ViewIntegrationManager` to prepare transition data (for smooth transitions between views).
    *   Updates the current view type in the `StateManager`.
    *   Calls `_render_view` to render the new view.

*   **`select_nodes(node_ids: Set[str])`:**
    *   Handles node selection.
    *   Updates the selected node IDs in the `StateManager`.
    *   Uses the `ViewIntegrationManager` to synchronize selection across views.
    *   Re-renders the view with the updated selection.

*   **`update_data()`:**
    *   Updates the data and re-renders the current view.

*   **`update_dimensions(width: float, height: float)`:**
    *   Updates the viewport dimensions and re-renders the view.

*   **`_render_view(nodes: List[VisualNode], edges: List[VisualEdge])`:**
    *   Renders the current view based on the provided nodes and edges.
    *   Retrieves the appropriate renderer from its internal dictionary based on the current `ViewType`.
    *   Calls the renderer's `render` method to perform the actual rendering.
    *   Caches the rendering result.

*   **`cleanup()`:**
    *   Cleans up resources.

**Dependencies:**

*   `DataInterface`: For accessing data.
*   `StateManager`: For managing view state (current view, zoom level, selected nodes, etc.).
*   `ViewIntegrationManager`: For handling interactions and synchronization between views.
*   `create_renderer`: For creating renderer instances for each view type.
*   `RenderConfig`: Configuration for the renderers.
* `VisualNode`, `VisualEdge`, `Viewport`: Data models.

### `models.py`

This file (located at `src/albumexplore/visualization/models.py`) defines the data models used for representing visual elements:

*   **`Point`:** Represents a 2D point with `x` and `y` coordinates.
*   **`Viewport`:** Represents the viewport configuration, including `x`, `y`, `width`, `height`, and `zoom`.
*   **`VisualNode`:** Represents a visual node in the graph.
    *   Attributes: `id`, `label`, `size`, `color`, `shape`, `data` (dictionary for custom data), `opacity`, `selected` (boolean), `visible` (boolean), `pos` (dictionary with 'x' and 'y' coordinates).
*   **`VisualEdge`:** Represents a visual edge connecting two nodes.
    *   Attributes: `source` (node ID), `target` (node ID), `weight`, `thickness`, `color`, `data` (dictionary for custom data), `opacity`, `visible` (boolean).

### `data_interface.py`

This file (located at `src/albumexplore/visualization/data_interface.py`) defines the `DataInterface` class, which acts as an abstraction layer for accessing data from the database and providing it in a format suitable for visualization.

**Key Components:**

*   **`DataConfig`:** A dataclass that holds configuration options for the data interface.
    *   Attributes: `max_nodes`, `max_edges`, `min_edge_weight`, `include_tags`, `filter_by_year`, `filter_by_genre`, `tag_threshold`.

*   **`DataInterface`:**
    *   **`__init__(session: Optional[Session] = None)`:** Initializes the interface with an optional database session and initializes internal caches for nodes, edges, and tags.
    *   **`configure(**kwargs)`:** Allows updating the configuration options.
    *   **`get_visible_data() -> Tuple[List[VisualNode], List[VisualEdge]]`:** Retrieves the currently visible nodes and edges, based on the configuration and potentially filtering criteria. It uses database queries to fetch data.
    *   **`_create_or_get_node(album: Album) -> Optional[VisualNode]`:** Creates or retrieves a `VisualNode` instance for a given `Album` object. It uses a cache to avoid creating duplicate nodes.
    *   **`_create_or_get_edge(source_id: str, target_id: str, weight: float) -> Optional[VisualEdge]`:** Creates or retrieves a `VisualEdge` instance for a given pair of source and target node IDs and a weight. It uses a cache to avoid creating duplicate edges.
    *   **`cleanup()`:** Cleans up resources, including closing the database session and clearing the caches.

**Dependencies:**

* `sqlalchemy.orm.Session`: For database interaction.
* `src.albumexplore.database.queries`:  Likely contains functions for querying the database (e.g., `get_albums_with_tags`).
* `src.albumexplore.database.models`:  Likely contains the database models (e.g., `Album`, `Tag`).
* `src.albumexplore.visualization.models`:  Contains the visualization data models (`VisualNode`, `VisualEdge`).

## Further Investigation
The next step is to add details about the implementation of specific views.

### `views/enhanced_network_view.py`

This file defines the `EnhancedNetworkView` class, which implements the network visualization.

**Key Features and Functionalities:**

*   **Inheritance:** Inherits from `BaseView`.
*   **Qt Integration:** Uses PyQt6 for GUI components and event handling.
*   **Optimized Rendering:** Employs a `DrawWidget` for optimized rendering using double-buffering. The `paintEvent` method of `DrawWidget` draws the current state from a pre-rendered pixmap buffer.
*   **Viewport Management:** Manages viewport parameters (`viewport_scale`, `viewport_x`, `viewport_y`) for zooming and panning.
*   **Data Handling:** Receives node and edge data through the `update_data` method.
*   **Spatial Indexing:** Uses a `SpatialGrid` for efficient node lookup during interaction.
*   **Level of Detail (LOD):** Includes an `LODSystem` for managing the level of detail.
*   **Clustering:** Supports node clustering using `ClusterManager` and `ClusterEngine`.
*   **Performance Optimization:** Uses a `PerformanceOptimizer` and tracks `PerformanceMetrics`.
*   **Interaction Handling:** Handles mouse events for dragging, selection, and zooming.
*   **Rendering Logic:** The `_paint_to_buffer` method handles the drawing of nodes, edges, and labels. It uses a `renderer` instance (obtained via `create_renderer`) to get the rendering data.
*   **Update Mechanism:** Uses a `QTimer` to schedule buffer updates.

**Dependencies:**
* `PyQt6`: For the GUI.
* `src.albumexplore.visualization.models`: For `VisualNode` and `VisualEdge`.
* `src.albumexplore.visualization.state`: For `ViewType` and `ViewState`.
* `src.albumexplore.visualization.spatial_grid`: For spatial indexing.
* `src.albumexplore.visualization.views.base_view`: Base class.
* `src.albumexplore.visualization.lod_system`: For level-of-detail management.
* `src.albumexplore.visualization.cluster_engine`: For node clustering.
* `src.albumexplore.visualization.performance_optimizer`: For performance optimization.
* `src.albumexplore.visualization.renderer`: For rendering.
* `src.albumexplore.gui.gui_logging`: For logging.

The rendering logic for each specific view type needs to be examined within their respective files (e.g., `enhanced_network_view.py`, `arc_view.py`, `chord_view.py`).

### `views/arc_view.py`

This file defines the `ArcView` class, implementing the arc diagram visualization.

**Key Features and Functionalities:**

*   **Inheritance:** Inherits from `BaseView`.
*   **Qt Integration:** Uses PyQt6 for drawing and event handling.
*   **Optimized Rendering:** Uses double buffering (`_paint_buffer`) for smoother rendering. The `paintEvent` method draws the buffered pixmap.
*   **`update_data`:** Marks the buffer as dirty, triggering a repaint.
*   **`paintEvent`:** Draws the pre-rendered content from the buffer to the widget.
*   **`_paint_to_buffer`:** Performs the actual rendering:
    *   Gets rendered data from the `renderer`.
    *   Draws arcs using `QPainterPath` and `quadTo` (quadratic curves).
    *   Draws nodes as ellipses.
    *   Draws labels with backgrounds.
*   **`resizeEvent`:** Handles resizing, marking the buffer as dirty.
*   **`hideEvent`:** Schedules resource cleanup.
*   **`_cleanup_resources`:** Cleans up resources (the buffer).
* **`mousePressEvent`:** Handles selection.

**Dependencies:**

*   `PyQt6`: For GUI components and drawing.
*   `.base_view`: Base class for views.
*   `..state`: For `ViewType` and `ViewState`.
*   `..renderer`: For creating the appropriate renderer.
* `albumexplore.gui.gui_logging`: For logging.

### `views/table_view.py`

This file defines the `TableView` class, which implements the table visualization using PyQt6's `QTableWidget`.

**Key Features and Functionalities:**

*   **Inheritance:** Inherits from `BaseView`.
*   **Qt Integration:** Uses PyQt6 for the table widget and event handling.
*   **Data Handling:** Receives data through the `update_data` method, which supports both a dictionary format (from a renderer) and direct updates with `VisualNode` objects.
*   **Table Configuration:** Sets up the table columns ("Artist", "Album", "Year", "Country", "Tags"), configures column widths, header behavior, selection behavior (row selection), and styling.
*   **Sorting:** Supports sorting by columns by handling header clicks.
*   **Selection Handling:** Manages selection of rows and emits a `selectionChanged` signal. Uses an internal flag to prevent recursion during selection updates.
* **Styling:** Sets a stylesheet to control appearance.
* **Update Mechanism:** The `update_data` method handles different data formats.

**Dependencies:**

*   `PyQt6`: For the GUI components (`QTableWidget`, etc.).
*   `src.albumexplore.visualization.views.base_view`: Base class for views.
*   `src.albumexplore.visualization.state`: For `ViewType` and `ViewState`.
*   `src.albumexplore.visualization.models`: For `VisualNode` (potentially `VisualEdge`, although not directly used in the provided code).
* `albumexplore.gui.gui_logging`: For logging.

### `views/chord_view.py`

This file defines the `ChordView` class, implementing the chord diagram visualization.

**Key Features and Functionalities:**

*   **Inheritance:** Inherits from `BaseView`.
*   **Qt Integration:** Uses PyQt6 for drawing and event handling.
*   **Optimized Rendering:** Uses double buffering (`_paint_buffer`) for smoother rendering. The `paintEvent` method draws the buffered pixmap.
*   **`update_data`:** Marks the buffer as dirty, triggering a repaint.
*   **`paintEvent`:** Draws the pre-rendered content from the buffer to the widget.
*   **`_paint_to_buffer`:** Performs the actual rendering:
    *   Gets rendered data from the `renderer`.
    *   Draws chords using `QPainterPath` and `cubicTo` (Bezier curves).
    *   Draws node arcs using `drawPie`.
    *   Draws labels with backgrounds.
*   **`resizeEvent`:** Handles resizing, marking the buffer as dirty.
*   **`hideEvent`:** Schedules resource cleanup.
*   **`_cleanup_resources`:** Cleans up resources (the buffer).
* **`mousePressEvent`:** Handles selection.

**Dependencies:**

*   `PyQt6`: For GUI components and drawing.
*   `.base_view`: Base class for views.
*   `..state`: For `ViewType` and `ViewState`.
*   `..renderer`: For creating the appropriate renderer.
* `albumexplore.gui.gui_logging`: For logging.
