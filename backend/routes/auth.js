const express = require('express');
const Shopkeeper = require('../models/Shopkeeper');
const router = express.Router();

router.post('/signup', async (req, res) => {
  try {
    const { fullName, email, password, phone, shopName, shopAddress, role } = req.body;

    // Basic server-side validation
    if (!email || !password) {
      return res.status(400).json({ message: 'Email and password are required' });
    }

    //It will check if email exists
    const existingUser = await Shopkeeper.findOne({ email });
    if (existingUser) {
      return res.status(400).json({ message: 'Email already exists' });
    }

    // Create new shopkeeper with role
    const shopkeeper = new Shopkeeper({
      fullName,
      email,
      password,
      phone,
      shopName,
      shopAddress,
      role: role || 'staff', // Default to staff
    });

    await shopkeeper.save();
    res.status(201).json({ message: 'Shopkeeper registered successfully' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error during signup' });
  }
});


router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    // Basic validation
    if (!email || !password) {
      return res.status(400).json({ message: 'Email and password are required' });
    }

    const shopkeeper = await Shopkeeper.findOne({ email });
    if (!shopkeeper || !(await shopkeeper.comparePassword(password))) {
      return res.status(401).json({ message: 'Invalid credentials' });
    }

    // In production, generate JWT here
    res.json({ 
      message: 'Login successful',
      user: { 
        id: shopkeeper._id, 
        email: shopkeeper.email, 
        shopName: shopkeeper.shopName,
        fullName: shopkeeper.fullName,
        role: shopkeeper.role || 'staff' // Include role in response
      }
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ message: 'Server error during login' });
  }
});

module.exports = router;