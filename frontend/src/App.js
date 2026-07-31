import React, { useEffect, useState } from 'react';
import axios from 'axios';
import 'bootstrap/dist/css/bootstrap.min.css';
import { HashRouter as Router, Routes, Route } from "react-router-dom";
import ScrollToTop from './components/ui/ScrollToTop';
import ProtectedRoute from './components/ProtectedRoute/ProtectedRoute';



import Container from "./components/Container/Container";
import Header from "./components/Header/Header";
import Footer from "./components/Footer/Footer";

import HomePage from './pages/HomePage';
import Participants from './pages/ParticipantsPage';
import AbstractsPage from './pages/AbstractsPage';
import RegistrationPage from './pages/RegistrationPage';
import ProgramPage from './pages/ProgramPage';
import AdminPanel from './components/AdminPanel/AdminPanel';
import ParticipantsInfo from './components/ParticipantsInfo/ParticipantsInfo';
import EditParticipants from './components/EditParticipants/EditParticipants';
import EditProgram from './components/EditProgram/EditProgram';
import EditWebInfo from './components/EditWebInfo/EditWebInfo';
import Venue from './components/Venue/Venue';
import Accommodation from './components/Accommodation/Accommodation';
import Hiking from './components/Hiking/Hiking';
import EditWebInfoHome from './components/EditWebInfoHome/EditWebInfoHome';
import EditWebInfoRegistration from './components/EditWebInfoRegistration/EditWebInfoRegistration';
import EditWebInfoProgram from './components/EditWebInfoProgram/EditWebInfoProgram';
import EditWebInfoVenue from './components/EditWebInfoVenue/EditWebInfoVenue';
import EditWebInfoAccommodation from './components/EditWebInfoAccommodation/EditWebInfoAccommodation';
import EditWebInfoHiking from './components/EditWebInfoHiking/EditWebInfoHiking';
import EditWebInfoFooter from './components/EditWebInfoFooter/EditWebInfoFooter';


function App() {
  return (
    <Router>
      <ScrollToTop/>
      <Container>
        <Header />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/participants" element={<Participants />} />
          <Route path="/abstracts" element={<AbstractsPage />} />
          <Route path="/registration" element={<RegistrationPage />} />
          <Route path="/program" element={<ProgramPage />} />
          <Route path="/venue" element={<Venue />} />
          <Route path="/accommodation" element={<Accommodation />} />
          <Route path="/hiking" element={<Hiking />} />
          {/* Protected Admin Routes */}
          <Route path="/admin-panel" element={
            <ProtectedRoute>
              <AdminPanel />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/participants-info" element={
            <ProtectedRoute>
              <ParticipantsInfo />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/edit-participants" element={
            <ProtectedRoute>
              <EditParticipants />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/edit-program" element={
            <ProtectedRoute>
              <EditProgram />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/edit-web-info" element={
            <ProtectedRoute>
              <EditWebInfo />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/edit-web-info/home" element={
            <ProtectedRoute>
              <EditWebInfoHome />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/edit-web-info/registration" element={
            <ProtectedRoute>
              <EditWebInfoRegistration />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/edit-web-info/program" element={
            <ProtectedRoute>
              <EditWebInfoProgram />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/edit-web-info/venue" element={
            <ProtectedRoute>
              <EditWebInfoVenue />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/edit-web-info/accommodation" element={
            <ProtectedRoute>
              <EditWebInfoAccommodation />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/edit-web-info/hiking" element={
            <ProtectedRoute>
              <EditWebInfoHiking />
            </ProtectedRoute>
          } />
          <Route path="/admin-panel/edit-web-info/footer" element={
            <ProtectedRoute>
              <EditWebInfoFooter />
            </ProtectedRoute>
          } />
        </Routes>
        <Footer />
      </Container>
    </Router>
  );
}

export default App;
