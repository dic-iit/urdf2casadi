# Copyright (C) 2021 Istituto Italiano di Tecnologia (IIT). All rights reserved.
# This software may be modified and distributed under the terms of the
# GNU Lesser General Public License v2.1 or any later version.

import casadi as cs
import numpy as np

from adam.casadi.casadi_like import SpatialMath
from adam.core import RBDAlgorithms
from adam.core.constants import Representations
from adam.model import Model, URDFModelFactory


class KinDynComputations:
    """This is a small class that retrieves robot quantities represented in a symbolic fashion using CasADi
    in mixed representation, for Floating Base systems - as humanoid robots.
    """

    def __init__(
        self,
        urdfstring: str,
        joints_name_list: list,
        root_link: str = "root_link",
        gravity: np.array = np.array([0.0, 0.0, -9.80665, 0.0, 0.0, 0.0]),
        f_opts: dict = dict(jit=False, jit_options=dict(flags="-Ofast")),
    ) -> None:
        """
        Args:
            urdfstring (str): path of the urdf
            joints_name_list (list): list of the actuated joints
            root_link (str, optional): the first link. Defaults to 'root_link'.
        """
        math = SpatialMath()
        factory = URDFModelFactory(path=urdfstring, math=math)
        model = Model.build(factory=factory, joints_name_list=joints_name_list)
        self.rbdalgos = RBDAlgorithms(model=model, math=math)
        self.NDoF = self.rbdalgos.NDoF
        self.g = gravity
        self.f_opts = f_opts

    def set_frame_velocity_representation(
        self, representation: Representations
    ) -> None:
        """Sets the representation of the velocity of the frames

        Args:
            representation (Representations): The representation of the velocity
        """
        self.rbdalgos.set_frame_velocity_representation(representation)

    def mass_matrix_fun(self) -> cs.Function:
        """Returns the Mass Matrix functions computed the CRBA

        Returns:
            M (casADi function): Mass Matrix
        """
        T_b = cs.SX.sym("T_b", 4, 4)
        s = cs.SX.sym("s", self.NDoF)
        [M, _] = self.rbdalgos.crba(T_b, s)
        return cs.Function("M", [T_b, s], [M.array], self.f_opts)

    def centroidal_momentum_matrix_fun(self) -> cs.Function:
        """Returns the Centroidal Momentum Matrix functions computed the CRBA

        Returns:
            Jcc (casADi function): Centroidal Momentum matrix
        """
        T_b = cs.SX.sym("T_b", 4, 4)
        s = cs.SX.sym("s", self.NDoF)
        [_, Jcm] = self.rbdalgos.crba(T_b, s)
        return cs.Function("Jcm", [T_b, s], [Jcm.array], self.f_opts)

    def forward_kinematics_fun(self, frame: str) -> cs.Function:
        """Computes the forward kinematics relative to the specified frame

        Args:
            frame (str): The frame to which the fk will be computed

        Returns:
            T_fk (casADi function): The fk represented as Homogenous transformation matrix
        """
        s = cs.SX.sym("s", self.NDoF)
        T_b = cs.SX.sym("T_b", 4, 4)
        T_fk = self.rbdalgos.forward_kinematics(frame, T_b, s)
        return cs.Function("T_fk", [T_b, s], [T_fk.array], self.f_opts)

    def jacobian_fun(self, frame: str) -> cs.Function:
        """Returns the Jacobian relative to the specified frame

        Args:
            frame (str): The frame to which the jacobian will be computed

        Returns:
            J_tot (casADi function): The Jacobian relative to the frame
        """
        s = cs.SX.sym("s", self.NDoF)
        T_b = cs.SX.sym("T_b", 4, 4)
        J_tot = self.rbdalgos.jacobian(frame, T_b, s)
        return cs.Function("J_tot", [T_b, s], [J_tot.array], self.f_opts)

    def relative_jacobian_fun(self, frame: str) -> cs.Function:
        """Returns the Jacobian between the root link and a specified frame frames

        Args:
            frame (str): The tip of the chain

        Returns:
            J (casADi function): The Jacobian between the root and the frame
        """
        s = cs.SX.sym("s", self.NDoF)
        J = self.rbdalgos.relative_jacobian(frame, s)
        return cs.Function("J", [s], [J.array], self.f_opts)

    def CoM_position_fun(self) -> cs.Function:
        """Returns the CoM positon

        Returns:
            com (casADi function): The CoM position
        """
        s = cs.SX.sym("s", self.NDoF)
        T_b = cs.SX.sym("T_b", 4, 4)
        com_pos = self.rbdalgos.CoM_position(T_b, s)
        return cs.Function("CoM_pos", [T_b, s], [com_pos.array], self.f_opts)

    def bias_force_fun(self) -> cs.Function:
        """Returns the bias force of the floating-base dynamics equation,
        using a reduced RNEA (no acceleration and external forces)

        Returns:
            h (casADi function): the bias force
        """
        T_b = cs.SX.sym("T_b", 4, 4)
        s = cs.SX.sym("s", self.NDoF)
        v_b = cs.SX.sym("v_b", 6)
        s_dot = cs.SX.sym("s_dot", self.NDoF)
        h = self.rbdalgos.rnea(T_b, s, v_b, s_dot, self.g)
        return cs.Function("h", [T_b, s, v_b, s_dot], [h.array], self.f_opts)

    def coriolis_term_fun(self) -> cs.Function:
        """Returns the coriolis term of the floating-base dynamics equation,
        using a reduced RNEA (no acceleration and external forces)

        Returns:
            C (casADi function): the Coriolis term
        """
        T_b = cs.SX.sym("T_b", 4, 4)
        q = cs.SX.sym("q", self.NDoF)
        v_b = cs.SX.sym("v_b", 6)
        q_dot = cs.SX.sym("q_dot", self.NDoF)
        # set in the bias force computation the gravity term to zero
        C = self.rbdalgos.rnea(T_b, q, v_b, q_dot, np.zeros(6))
        return cs.Function("C", [T_b, q, v_b, q_dot], [C.array], self.f_opts)

    def gravity_term_fun(self) -> cs.Function:
        """Returns the gravity term of the floating-base dynamics equation,
        using a reduced RNEA (no acceleration and external forces)

        Returns:
            G (casADi function): the gravity term
        """
        T_b = cs.SX.sym("T_b", 4, 4)
        q = cs.SX.sym("q", self.NDoF)
        # set in the bias force computation the velocity to zero
        G = self.rbdalgos.rnea(T_b, q, np.zeros(6), np.zeros(self.NDoF), self.g)
        return cs.Function("G", [T_b, q], [G.array], self.f_opts)

    def forward_kinematics(self, frame, T_b, s) -> cs.Function:
        """Computes the forward kinematics relative to the specified frame

        Args:
            frame (str): The frame to which the fk will be computed

        Returns:
            T_fk (casADi function): The fk represented as Homogenous transformation matrix
        """

        return self.rbdalgos.forward_kinematics(frame, T_b, s)

    def get_total_mass(self) -> float:
        """Returns the total mass of the robot

        Returns:
            mass: The total mass
        """
        return self.rbdalgos.get_total_mass()
