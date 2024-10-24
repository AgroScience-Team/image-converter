db = db.getSiblingDB('file_link_hub');
db.createUser({
    user: 'file_link_hub',
    pwd: 'password',
    roles: [{ role: 'readWrite', db: 'file_link_hub' }]
});

db.createUser({
    user: 'files_reader',
    pwd: 'password',
    roles: [{ role: 'read', db: 'file_link_hub' }]
});
