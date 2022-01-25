// example:
// https://codepen.io/brendandougan/pen/PpEzRp

// tree with tabular data
// https://observablehq.com/@d3/indented-tree

"use strict";

/*jshint esversion: 6 */
(function () {
    "use strict";
}());

const NODE_SIZE = 25;
const ICON_TRUE = "\u2713";
const ICON_FALSE = "\u2716"; // "\u00d7";
const ICON_MAYBE = "";

function selectionIcon(value, automatic) {
  if (value) { return automatic ? `(${ICON_TRUE})` : ICON_TRUE; }
  if (value === false) { return automatic ? `(${ICON_FALSE})` : ICON_FALSE; }
  return ICON_MAYBE;
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

        this.onBulletClick = (event, d) => {
            if (!d.children && !d._children) {
                return this.onFeatureLabelClick(event, d)
            }
            event.preventDefault();
            event.stopImmediatePropagation();
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

        this.onFeatureLabelClick = (event, d) => {
            event.preventDefault();
            event.stopImmediatePropagation();
            // skip the root
            if (d.depth == 0) { return; }
            const radio = d.parent.ui.xor === true;
            if (d.ui.selected !== d.data.selected) {
                d.ui.selected = d.data.selected;
            } else {
                if (radio) {
                    if (d.data.selected) {
                        d.data.selected = null;
                        d.ui.selected = null;
                    } else {
                        if (d.data.resolved === false) {
                            let v = window.prompt("Value:", "");
                            if (v) {
                                d.ui.inputValue = v;
                                d.ui.name = v;
                            } else {
                                return;
                            }
                        }
                        d.data.selected = true;
                        d.ui.selected = true;
                    }
                } else {
                    if (d.data.selected) {
                      d.data.selected = false;
                      d.ui.selected = false;
                    } else if (d.data.selected === false) {
                      d.data.selected = null;
                      d.ui.selected = null;
                    } else {
                      if (d.data.resolved === false) {
                        let v = window.prompt("Value:", "");
                        if (v) {
                          d.ui.inputValue = v;
                        } else {
                          return;
                        }
                      }
                      d.data.selected = true;
                      d.ui.selected = true;
                    }
                }
            }
            this.propagateSelection(d);
            this.render();
        };

        this.propagateSelection = (source) => {
            var n = source.parent;
            // radio button behaviour
            if (n.ui.xor) {
                let v = source.data.selected ? false : null;
                let children = n.children || n._children;
                for (const o of children) {
                    if (o === source) { continue; }
                    o.data.selected = v;
                    o.ui.selected = v;
                }
            }
            // skip the root
            while (n != null && n.depth > 0) {
                this.recalculateValue(n);
                n = n.parent;
            }
            let value = source.data.selected;
            if (value || !source.data.children) { return; }
            var fv;
            if (value == null) {
                fv = (d) => { return d.ui.selected; };
            } else {
                fv = () => { return value; }
            }
            let stack = [...(source.children || source._children)];
            while (stack.length > 0) {
                let datum = stack.pop();
                datum.data.selected = fv(datum);
                if (datum.data.children) {
                    for (var child of (datum.children || datum._children)) {
                        stack.push(child);
                    }
                }
            }
        };

        this.recalculateValue = (d) => {
            if (d.parent != null) {
                if (d.parent.data.selected === false) {
                    d.data.selected = false;
                    return;
                }
            }
            if (!d.children) { return; }
            var value = null;
            for (var child of d.children) {
                if (child.data.selected) { value = true; }
            }
            d.data.selected = value || d.ui.selected;
        };

        this.render = (nodes) => {
            if (!nodes) { nodes = this.svg.selectAll("g.tree-node"); }
            nodes.each(function (d) {
                let selected = false;
                let discarded = false;
                let icon = ICON_MAYBE;
                let automatic = d.data.selected !== d.ui.selected;
                if (d.depth == 0) { return; }
                if (d.data.selected) {
                    icon = ICON_TRUE;
                    selected = true;
                } else if (d.data.selected === false) {
                    icon = ICON_FALSE;
                    discarded = true;
                } else if (d.ui.selected) {
                    icon = ICON_TRUE;
                    selected = true;
                } else if (d.ui.selected === false) {
                    icon = ICON_FALSE;
                    discarded = true;
                }
                let label = d3.select(this)
                    .select("text.feature-label")
                    .classed("selected", selected)
                    .classed("discarded", discarded);
                if (d.ui.name != d.data.name) {
                  console.log(d.ui.name, d.data.name);
                }
                label.select("tspan.feature-name")
                    .text(d.ui.name);
                label.select("tspan.text-icon")
                    .text(automatic ? `(${icon})` : icon);
            });
        };

        this.update = (source) => {
            // Compute the new tree layout.
            let nodes = this.tree(this.root);
            let nodesSort = [];
            nodes.eachBefore(function (n) {
                nodesSort.push(n);
            });
            // this.height = Math.max(500, nodesSort.length * this.barHeight + this.margin.top + this.margin.bottom);
            this.height = Math.max(300, nodesSort.length * this.barHeight + this.margin.top + this.margin.bottom);
            let links = nodesSort.slice(1);
            // Compute the "layout".
            nodesSort.forEach((n, i) => {
                n.x = i * this.barHeight;
            });
            //d3.select("svg").transition()
            this.svg.transition()
                .duration(this.duration)
                .attr("height", this.height);
            this.svgElement.transition()
                .duration(this.duration)
                .style("height", this.height + "px");

            // Update the nodes…
            let node = this.svg.selectAll("g.tree-node")
                .data(nodesSort, function (d) {
                    return d.id || (d.id = ++this.i);
                });

            // Enter any new nodes at the parent's previous position.
            let nodeEnter = node.enter().append("g")
                .classed("tree-node", true)
                .attr("transform", function () {
                    return "translate(" + source.y0 + "," + source.x0 + ")";
                })
                .on("click", this.onBulletClick);
            nodeEnter.append("circle")
                .attr("r", 1e-6);
            let tlabel = nodeEnter.append("text")
                .classed("feature-label", true)
                .attr("x", NODE_SIZE / 2)
                .attr("dy", ".35em")
                .attr("text-anchor", "start")
                .style("fill-opacity", 1e-6)
                .on("click", this.onFeatureLabelClick);
            tlabel.append("tspan")
                .classed("feature-name", true)
                .text(function (d) {
                    if (d.data.name.length > 30) {
                        return "..." + d.data.name.substring(d.data.name.length - 30);
                    }
                    else {
                        return d.data.name;
                    }
                });
            tlabel.append("tspan")
                .classed("text-icon", true)
                .attr("dx", ".5em")
                .text(function (d) { return selectionIcon(d.data.selected); });
            nodeEnter.append("svg:title").text(function (d) {
                return d.ancestors().reverse().map((d) => { return d.data.name; }).join("/");
            });

            // Transition nodes to their new position.
            let nodeUpdate = node.merge(nodeEnter)
                .transition()
                .duration(this.duration);
            nodeUpdate
                .attr("transform", function (d) {
                    return "translate(" + d.y + "," + d.x + ")";
                });
            nodeUpdate.select("circle")
                .attr("r", NODE_SIZE / 4)
                .style("fill", function (d) {
                    return d._children != null ? "lightsteelblue" : "white";
                });
            nodeUpdate.selectAll("text")
                .style("fill-opacity", 1);

            // Transition exiting nodes to the parent's new position (and remove the nodes)
            var nodeExit = node.exit().transition()
                .duration(this.duration);
            nodeExit
                .attr("transform", function (d) {
                    return "translate(" + source.y + "," + source.x + ")";
                })
                .remove();
            nodeExit.select("circle")
                .attr("r", 1e-6);
            nodeExit.selectAll("text")
                .style("fill-opacity", 1e-6);

            // Update the links…
            var link = this.svg.selectAll("path.link")
                .data(links, function (d) {
                    // return d.target.id;
                    var id = d.id + "->" + d.parent.id;
                    return id;
                });
            // Enter any new links at the parent's previous position.
            let linkEnter = link.enter().insert("path", "g")
                .attr("class", "link")
                .attr("d", (d) => {
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
                .attr("d", this.connector);

            // // Transition exiting nodes to the parent's new position.
            link.exit().transition()
                .duration(this.duration)
                .attr("d", (d) => {
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
        this.barHeight = NODE_SIZE;
        this.barWidth = this.width * .8;
        this.i = 0;
        this.duration = 450;
        this.tree = d3.tree().size([this.width, this.height]);
        this.tree.nodeSize([0, NODE_SIZE]);
        this.root = this.tree(d3.hierarchy(data));
        this.root.each((d) => {
            d.name = d.id; //transferring name to a name variable
            d.id = this.i; //Assigning numerical Ids
            this.i++;
            d.ui = {
                name: d.data.name,
                selected: d.data.selected,
                xor: d.data.type === 'arg'
            };
        });
        this.root.x0 = this.root.x;
        this.root.y0 = this.root.y;

        this.svgElement = d3.select("#feature-model-container").append("svg");
            //.attr("width", this.width + this.margin.right + this.margin.left + "px")
            //.attr("height", this.height + this.margin.top + this.margin.bottom + "px")

        this.svg = this.svgElement.append("g")
            .attr("transform", "translate(" + this.margin.left + "," + this.margin.top + ")");

        this.root.children.forEach(this.collapse);
        this.update(this.root);
        this.render();
    }

    setWidth(w) {
        this.width = w - this.margin.right;
    }

    getModelData() {
        return this.root.data;
    }

    syncModelData(data) {
        console.log('sync model data');

        this.i = 0;
        this.root = this.tree(d3.hierarchy(data));
        this.root.each((d) => {
            d.name = d.id; //transferring name to a name variable
            d.id = this.i; //Assigning numerical Ids
            this.i++;
        });
        this.root.x0 = this.root.x;
        this.root.y0 = this.root.y;

        this.update(this.root);
        this.render();
    }
};
