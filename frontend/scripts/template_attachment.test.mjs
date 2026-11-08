import test from 'node:test';
import assert from 'node:assert/strict';
import { attachmentVersion } from '../src/templateAttachmentSelection.js';
test('existing pin survives a newer published template',()=>assert.equal(attachmentVersion({version:2},{template_version:1}),1));
test('new attachment selects current published version',()=>assert.equal(attachmentVersion({version:3},null),3));
test('malformed persisted pin cannot silently select latest',()=>{for(const v of [null,0,-1,'1',undefined]) assert.throws(()=>attachmentVersion({version:3},{template_version:v}));});
