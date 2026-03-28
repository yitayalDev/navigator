import 'package:flutter/material.dart';

/// A draggable floating action button that can be positioned anywhere on screen
class DraggableFAB extends StatefulWidget {
  final IconData icon;
  final String label;
  final Color backgroundColor;
  final Color foregroundColor;
  final VoidCallback onPressed;
  final double initialX;
  final double initialY;

  const DraggableFAB({
    super.key,
    required this.icon,
    required this.label,
    required this.backgroundColor,
    required this.foregroundColor,
    required this.onPressed,
    this.initialX = 20,
    this.initialY = 100,
  });

  @override
  State<DraggableFAB> createState() => _DraggableFABState();
}

class _DraggableFABState extends State<DraggableFAB> {
  late double _x;
  late double _y;
  bool _isDragging = false;

  @override
  void initState() {
    super.initState();
    _x = widget.initialX;
    _y = widget.initialY;
  }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.topLeft,
      child: Padding(
        padding: EdgeInsets.only(
          left: _x,
          top: _y,
        ),
        child: GestureDetector(
          onPanStart: (_) {
            setState(() {
              _isDragging = true;
            });
          },
          onPanUpdate: (details) {
            setState(() {
              _x += details.delta.dx;
              _y += details.delta.dy;
              
              // Keep within screen bounds
              _x = _x.clamp(0, MediaQuery.of(context).size.width - 100);
              _y = _y.clamp(0, MediaQuery.of(context).size.height - 100);
            });
          },
          onPanEnd: (_) {
            setState(() {
              _isDragging = false;
            });
          },
          child: AnimatedScale(
            scale: _isDragging ? 1.1 : 1.0,
            duration: const Duration(milliseconds: 100),
            child: FloatingActionButton.extended(
              heroTag: 'draggable_ai',
              onPressed: widget.onPressed,
              backgroundColor: widget.backgroundColor,
              foregroundColor: widget.foregroundColor,
              icon: Icon(widget.icon),
              label: Text(widget.label),
            ),
          ),
        ),
      ),
    );
  }
}

/// A simpler draggable icon button (for AI chat)
class DraggableIconButton extends StatefulWidget {
  final IconData icon;
  final Color color;
  final VoidCallback onPressed;
  final double initialX;
  final double initialY;
  final String tooltip;

  const DraggableIconButton({
    super.key,
    required this.icon,
    required this.color,
    required this.onPressed,
    this.initialX = 20,
    this.initialY = 150,
    this.tooltip = '',
  });

  @override
  State<DraggableIconButton> createState() => _DraggableIconButtonState();
}

class _DraggableIconButtonState extends State<DraggableIconButton> {
  late double _x;
  late double _y;
  bool _isDragging = false;

  @override
  void initState() {
    super.initState();
    _x = widget.initialX;
    _y = widget.initialY;
  }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.topLeft,
      child: Padding(
        padding: EdgeInsets.only(
          left: _x,
          top: _y,
        ),
        child: GestureDetector(
          onPanStart: (_) {
            setState(() {
              _isDragging = true;
            });
          },
          onPanUpdate: (details) {
            setState(() {
              _x += details.delta.dx;
              _y += details.delta.dy;
              
              // Keep within screen bounds
              final maxX = MediaQuery.of(context).size.width - 60;
              final maxY = MediaQuery.of(context).size.height - 60;
              _x = _x.clamp(0, maxX > 0 ? maxX : 0);
              _y = _y.clamp(0, maxY > 0 ? maxY : 0);
            });
          },
          onPanEnd: (_) {
            setState(() {
              _isDragging = false;
            });
          },
          child: Tooltip(
            message: widget.tooltip,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 100),
              transform: Matrix4.identity()..scale(_isDragging ? 1.2 : 1.0),
              child: FloatingActionButton.small(
                heroTag: 'draggable_icon_${widget.icon.codePoint}',
                onPressed: widget.onPressed,
                backgroundColor: widget.color,
                child: Icon(
                  widget.icon,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}