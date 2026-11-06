const express = require('express');
const { MongoClient } = require('mongodb');
const { dealerships } = require('./data/dealerships.json');
const { reviews } = require('./data/reviews.json');

async function start() {
  const client = new MongoClient(process.env.MONGODB_URL || 'mongodb://127.0.0.1:27017');
  await client.connect();
  const db = client.db('dealershipsDB');
  const branches = db.collection('dealerships');
  const feedback = db.collection('reviews');
  await branches.createIndex({ id: 1 }, { unique: true });
  await feedback.createIndex({ dealership: 1 });
  await branches.bulkWrite(dealerships.map(dealer => ({
    updateOne: { filter: { id: dealer.id }, update: { $setOnInsert: dealer }, upsert: true },
  })));
  await feedback.bulkWrite(reviews.map(review => ({
    updateOne: { filter: { id: review.id }, update: { $setOnInsert: review }, upsert: true },
  })));

  const app = express();
  app.use(express.json({ limit: '12kb' }));
  const route = fn => (req, res, next) => Promise.resolve(fn(req, res)).catch(next);
  app.get('/', (req, res) => res.json({ status: 'ready' }));
  app.get('/fetchDealers/:state?', route(async (req, res) => {
    const state = req.params.state;
    const filter = state ? { $or: [{ state }, { st: state.toUpperCase() }] } : {};
    res.json(await branches.find(filter, { projection: { _id: 0 } }).sort({ id: 1 }).toArray());
  }));
  app.get('/fetchDealer/:id', route(async (req, res) => {
    const dealer = await branches.findOne({ id: Number(req.params.id) }, { projection: { _id: 0 } });
    if (!dealer) return res.status(404).json({ error: 'Dealer not found.' });
    res.json(dealer);
  }));
  app.get('/fetchReviews/dealer/:id', route(async (req, res) => {
    res.json(await feedback.find({ dealership: Number(req.params.id) }, { projection: { _id: 0 } }).sort({ _id: -1 }).toArray());
  }));
  app.post('/insert_review', route(async (req, res) => {
    const data = req.body;
    if (!Number.isInteger(data.dealership) || typeof data.review !== 'string' || !data.review.trim()) {
      return res.status(400).json({ error: 'Invalid review.' });
    }
    if (!(await branches.findOne({ id: data.dealership }))) return res.status(404).json({ error: 'Dealer not found.' });
    const { insertedId } = await feedback.insertOne(data);
    res.status(201).json({ ...data, id: insertedId.toString() });
  }));
  app.use((error, req, res, next) => {
    console.error(error);
    res.status(error.status || 500).json({ error: 'Dealer service request failed.' });
  });
  app.listen(Number(process.env.PORT || 3030), '0.0.0.0', () => console.log('Dealer API ready'));
}

start().catch(error => { console.error(error); process.exitCode = 1; });
