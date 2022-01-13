// example:
// https://codepen.io/brendandougan/pen/PpEzRp

"use strict";

/*jshint esversion: 6 */
(function () {
    'use strict';
}());

let tree = d3.tree;
let hierarchy = d3.hierarchy;
let select = d3.select;

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
        };
        this.update = (source) => {
            this.width = 800;
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
            //d3.select('svg').transition()
            this.svg.transition()
                .duration(this.duration)
                .attr("height", this.height);
            d3.select('#hierarchy-container>svg')
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
            nodeEnter.append('svg:title').text(function (d) {
                return d.data.name;
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
                .attr('r', 4.5)
                .style('fill', function (d) {
                return d._children ? 'lightsteelblue' : '#fff';
            });
            nodeUpdate.select('text')
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
            nodeExit.select('text')
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
                var o = { x: source.x0, y: source.y0, parent: { x: source.x0, y: source.y0 } };
                return this.connector(o);
            });
            // Transition links to their new position.
            link.merge(linkEnter).transition()
                .duration(this.duration)
                .attr('d', this.connector);
            // // Transition exiting nodes to the parent's new position.
            link.exit().transition()
                .duration(this.duration)
                .attr('d', (d) => {
                var o = { x: source.x, y: source.y, parent: { x: source.x, y: source.y } };
                return this.connector(o);
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
        this.margin = { top: 20, right: 10, bottom: 20, left: 10 };
        this.width = 1400 - this.margin.right - this.margin.left;
        this.height = 800 - this.margin.top - this.margin.bottom;
        this.barHeight = 20;
        this.barWidth = this.width * .8;
        this.i = 0;
        this.duration = 450;
        this.tree = tree().size([this.width, this.height]);
        this.tree.nodeSize([0, 30]);
        this.root = this.tree(hierarchy(data));
        this.root.each((d) => {
            d.name = d.id; //transferring name to a name variable
            d.id = this.i; //Assigning numerical Ids
            this.i++;
        });
        this.root.x0 = this.root.x;
        this.root.y0 = this.root.y;
        this.svg = select('#hierarchy-container').append('svg')
            //.attr('width', this.width + this.margin.right + this.margin.left + 'px')
            //.attr('height', this.height + this.margin.top + this.margin.bottom + 'px')
            .append('g')
            .attr('transform', 'translate(' + this.margin.left + ',' + this.margin.top + ')');
        // this.root.children.forEach(this.collapse);
        this.update(this.root);
    }
}
;
//let myTree = new MyTree();
//myTree.$onInit();
