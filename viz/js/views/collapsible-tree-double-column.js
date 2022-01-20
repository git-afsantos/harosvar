// example:
// https://codepen.io/brendandougan/pen/PpEzRp

// tree with tabular data
// https://observablehq.com/@d3/indented-tree

"use strict";

/*jshint esversion: 6 */
(function () {
    'use strict';
}());

function conditionToString(value, automatic) {
    let suffix = automatic ? " (!)" : "";
    switch (value) {
        case null:
            return `<unknown>${suffix}`;
        case true:
            return `true${suffix}`;
        case false:
            return `false${suffix}`;
        default:
            return `${value}${suffix}`;
    }
}

class MyTree {
    constructor() {
        this.connector = function (d) {
            //curved
            /*return "M" + d.y + "," + d.x +
               "C" + (d.y + d.parent.y) / 2 + "," + d.x +
               " " + (d.y + d.parent.y) / 2 + "," + d.parent.x +
               " " + d.parent.y + "," + d.parent.x;*/
            //straight
            return "M" + d.parent.y + "," + d.parent.x
                + "V" + d.x + "H" + d.y;
        };

        this.collapse = (d) => {
            if (d.children) {
                d._children = d.children;
                d._children.forEach(this.collapse);
                d.children = null;
            }
        };

        this.click = (event, d) => {
            if (d.children) {
                d._children = d.children;
                d.children = null;
            }
            else {
                d.children = d._children;
                d._children = null;
            }

            this.update(d);
            this.render();
        };

        this.onValueLabelClick = (event, d) => {
            event.preventDefault();
            event.stopImmediatePropagation();
            // skip the root
            if (d.depth == 0) { return; }
            if (d.data.value) {
                d.data.value = false;
                d.data.userValue = false;
            } else if (d.data.value === false) {
                d.data.value = null;
                d.data.userValue = null;
            } else {
                d.data.value = true;
                d.data.userValue = true;
            }
            this.propagateSelection(d);
            this.render();
        };

        this.propagateSelection = (source) => {
            var n = source.parent;
            // skip the root
            while (n != null && n.depth > 0) {
                this.recalculateValue(n);
                n = n.parent;
            }
            let value = source.data.value;
            if (value || !source.data.children) { return; }
            var fv;
            if (value == null) {
                fv = (d) => { return d.userValue; };
            } else {
                fv = () => { return value; }
            }
            let stack = [...source.data.children];
            while (stack.length > 0) {
                let datum = stack.pop();
                datum.value = fv(datum);
                if (datum.children) {
                    for (var child of datum.children) {
                        stack.push(child);
                    }
                }
            }
        };

        this.recalculateValue = (d) => {
            if (!d.children) { return; }
            var value = null;
            for (var child of d.children) {
                if (child.data.value) { value = true; }
            }
            d.data.value = value || d.data.userValue;
        };

        this.render = (nodes) => {
            if (!nodes) { nodes = this.svg.selectAll('g.tree-node'); }
            nodes.each(function (d) {
                var text, color;
                let automatic = d.data.value !== d.data.userValue;
                // if (d.depth == 0) { return; }
                if (d.data.value) {
                    color = "forestgreen";
                    text = conditionToString(true, automatic);
                } else if (d.data.value === false) {
                    color = "firebrick";
                    text = conditionToString(false, automatic);
                } else if (d.data.userValue) {
                    color = "forestgreen";
                    text = conditionToString(true, automatic);
                } else if (d.data.userValue === false) {
                    color = "firebrick";
                    text = conditionToString(false, automatic);
                } else {
                    color = "black"
                    text = conditionToString(null, automatic);
                }
                let node = d3.select(this);
                node.select("text").style("fill", color);
                node.select("text.value-label").text(text);
            });
        };

        this.update = (source) => {
            // Compute the new tree layout.
            let nodes = this.tree(this.root);
            let nodesSort = [];
            nodes.eachBefore(function (n) {
                nodesSort.push(n);
                if (n.data.value === undefined) { n.data.value = null; }
                if (n.data.userValue === undefined) { n.data.userValue = null; }
            });
            // this.height = Math.max(500, nodesSort.length * this.barHeight + this.margin.top + this.margin.bottom);
            this.height = Math.max(300, nodesSort.length * this.barHeight + this.margin.top + this.margin.bottom);
            let links = nodesSort.slice(1);
            // Compute the "layout".
            nodesSort.forEach((n, i) => {
                n.x = i * this.barHeight;
            });
            //d3.select('svg').transition()
            this.svg.transition()
                .duration(this.duration)
                .attr("height", this.height);
            this.svgElement.transition()
                .duration(this.duration)
                .style("height", this.height + 'px');

            // Update the nodes…
            let node = this.svg.selectAll('g.tree-node')
                .data(nodesSort, function (d) {
                    return d.id || (d.id = ++this.i);
                });

            // Enter any new nodes at the parent's previous position.
            var nodeEnter = node.enter().append('g')
                .attr('class', 'tree-node')
                .attr('transform', function () {
                    return 'translate(' + source.y0 + ',' + source.x0 + ')';
                })
                .on('click', this.click);
            nodeEnter.append('circle')
                .attr('r', 1e-6)
                .style('fill', function (d) {
                    return d._children ? 'lightsteelblue' : '#fff';
                });
            nodeEnter.append('text')
                .attr('x', function (d) {
                    return d.children || d._children ? 10 : 10;
                })
                .attr('dy', '.35em')
                .attr('text-anchor', function (d) {
                    return d.children || d._children ? 'start' : 'start';
                })
                .text(function (d) {
                    if (d.data.name.length > 20) {
                        return d.data.name.substring(0, 20) + '...';
                    }
                    else {
                        return d.data.name;
                    }
                })
                .style('fill-opacity', 1e-6);
            nodeEnter.append("text")
                .attr('class', 'value-label')
                .attr("dx", function (d) {
                    return -20 * (d.depth + 1);
                })
                .attr("dy", ".35em")
                .attr("x", this.width)
                .attr("text-anchor", "end")
                .text(function (d) {
                    if (d.depth == 0) { return "true"; }
                    return conditionToString(d.data.value, true);
                })
                .style('fill-opacity', 1e-6)
                .on('click', this.onValueLabelClick);
            nodeEnter.append('svg:title').text(function (d) {
                return d.ancestors().reverse().map((d) => { return d.data.name; }).join("/");
            });

            // Transition nodes to their new position.
            let nodeUpdate = node.merge(nodeEnter)
                .transition()
                .duration(this.duration);
            nodeUpdate
                .attr('transform', function (d) {
                    return 'translate(' + d.y + ',' + d.x + ')';
                });
            nodeUpdate.select('circle')
                .attr('r', 5)
                .style('fill', function (d) {
                    return d._children ? 'lightsteelblue' : '#fff';
                });
            nodeUpdate.selectAll('text')
                .style('fill-opacity', 1);

            // Transition exiting nodes to the parent's new position (and remove the nodes)
            var nodeExit = node.exit().transition()
                .duration(this.duration);
            nodeExit
                .attr('transform', function (d) {
                    return 'translate(' + source.y + ',' + source.x + ')';
                })
                .remove();
            nodeExit.select('circle')
                .attr('r', 1e-6);
            nodeExit.selectAll('text')
                .style('fill-opacity', 1e-6);

            // Update the links…
            var link = this.svg.selectAll('path.link')
                .data(links, function (d) {
                    // return d.target.id;
                    var id = d.id + '->' + d.parent.id;
                    return id;
                });
            // Enter any new links at the parent's previous position.
            let linkEnter = link.enter().insert('path', 'g')
                .attr('class', 'link')
                .attr('d', (d) => {
                    return this.connector({
                        x: source.x0,
                        y: source.y0,
                        parent: {
                            x: source.x0,
                            y: source.y0
                        }
                    });
                });

            // Transition links to their new position.
            link.merge(linkEnter).transition()
                .duration(this.duration)
                .attr('d', this.connector);

            // // Transition exiting nodes to the parent's new position.
            link.exit().transition()
                .duration(this.duration)
                .attr('d', (d) => {
                    return this.connector({
                        x: source.x,
                        y: source.y,
                        parent: {
                            x: source.x,
                            y: source.y
                        }
                    });
                })
                .remove();

            // Stash the old positions for transition.
            nodesSort.forEach(function (d) {
                d.x0 = d.x;
                d.y0 = d.y;
            });
        };
    }

    $onInit(data) {
        this.margin = { top: 20, right: 10, bottom: 20, left: 20 };
        this.width = 1400 - this.margin.right - this.margin.left;
        this.height = 800 - this.margin.top - this.margin.bottom;
        this.barHeight = 20;
        this.barWidth = this.width * .8;
        this.i = 0;
        this.duration = 450;
        this.tree = d3.tree().size([this.width, this.height]);
        this.tree.nodeSize([0, 20]);
        this.root = this.tree(d3.hierarchy(data));
        this.root.each((d) => {
            d.name = d.id; //transferring name to a name variable
            d.id = this.i; //Assigning numerical Ids
            this.i++;
        });
        this.root.x0 = this.root.x;
        this.root.y0 = this.root.y;

        this.svgElement = d3.select('#feature-model-container').append('svg');
            //.attr('width', this.width + this.margin.right + this.margin.left + 'px')
            //.attr('height', this.height + this.margin.top + this.margin.bottom + 'px')

        this.svg = this.svgElement.append('g')
            .attr('transform', 'translate(' + this.margin.left + ',' + this.margin.top + ')');

        this.labelFeature = this.svg.append("text")
            .attr("dx", "-0.5em")
            .attr("y", 0)
            .attr("x", 0)
            //.attr("text-anchor", "end")
            .attr("font-weight", "bold")
            .text("Feature");

        this.labelValue = this.svg.append("text")
            .attr("dx", -20)
            .attr("y", 0)
            .attr("x", this.width)
            .attr("text-anchor", "end")
            .attr("font-weight", "bold")
            .text("Value");

        let offsetY = this.margin.top + 20;
        this.svg = this.svgElement.append('g')
            .attr('transform', 'translate(' + this.margin.left + ',' + offsetY + ')');

        this.root.children.forEach(this.collapse);
        this.update(this.root);
        this.render();
    }

    setWidth(w) {
        this.width = w - this.margin.right;
        this.labelValue.attr("x", this.width);
        this.svg.selectAll('text.value-label')
            .attr("x", this.width);
    }
};
