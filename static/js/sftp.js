$(function() {
    $('#sftp').jstree({
      'core': {
        'data': [
          { "text": "一级 1", "children": [{ "text": "二级 1-1", "children": [{ "text": "三级 1-1-1" }] }] },
          { "text": "一级 2", "children": [{ "text": "二级 2-1", "children": [{ "text": "三级 2-1-1" }] }, { "text": "二级 2-2", "children": [{ "text": "三级 2-2-1" }] }] },
          { "text": "一级 3", "children": [{ "text": "二级 3-1", "children": [{ "text": "三级 3-1-1" }] }] }
        ]
      }
    });
  });